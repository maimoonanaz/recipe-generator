import streamlit as st
from typing import Optional
import time
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont

# ---------------- Streamlit Page ----------------
st.set_page_config(page_title="Recipe Chatbot", page_icon="🥘", layout="centered")
st.title("🥘 Recipe Chatbot")
st.caption("Type a recipe name and preferences — chatbot will generate a complete recipe.")

# ---------------- Secrets Check ----------------
if not st.secrets.get("GEMINI_API_KEY"):
    st.warning("Streamlit secrets not found. Make sure .streamlit/secrets.toml exists with GEMINI_API_KEY.")
else:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- Helper Functions ----------------
def build_prompt(recipe_name: str,
                 cuisine: Optional[str],
                 servings: Optional[int],
                 dietary: Optional[str],
                 extra_req: Optional[str]) -> str:
    prompt = f"Write a complete recipe for '{recipe_name}'.\n"
    if cuisine:
        prompt += f"Cuisine: {cuisine}.\n"
    if servings:
        prompt += f"Adjust quantities for {servings} serving(s).\n"
    if dietary:
        prompt += f"Dietary preference: {dietary}.\n"
    if extra_req:
        prompt += f"Additional requirements: {extra_req}.\n"
    prompt += (
        "Return the recipe in clear sections: Title, Short description, "
        "Ingredients (bullet list), Steps (numbered), Cooking time, "
        "Prep time, Total time, Servings, Optional substitutions, Nutrition estimates. "
        "Keep language simple and friendly for home cooks."
    )
    return prompt

def call_gemini(prompt: str):
    """Gemini API call using GenerativeModel.generate_content"""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini API Error: {e}\nTry CLI fallback."

def generate_image(recipe_name: str):
    """Generate image for the recipe"""
    try:
        url = genai.generate_image(recipe_name)
        return url
    except Exception as e:
        # Fallback PIL image if API fails
        img = Image.new('RGB', (400, 300), color='lightyellow')
        d = ImageDraw.Draw(img)
        d.text((10, 10), f"{recipe_name}", fill=(0, 0, 0))
        return img

# ---------------- Session State ----------------
if "history" not in st.session_state:
    st.session_state.history = []

# ---------------- Form Inputs ----------------
with st.form(key="recipe_form"):
    col1, col2 = st.columns([3,1])
    with col1:
        recipe_name = st.text_input("Recipe name (e.g., Chicken Biryani, Chocolate Mug Cake)", "")
    with col2:
        cuisine = st.selectbox("Cuisine (optional)", ["", "Pakistani", "Indian", "Chinese", "Italian", "American", "Middle Eastern", "Mexican", "Other"])
    servings = st.number_input("Servings", min_value=1, max_value=20, value=2, step=1)
    dietary = st.selectbox("Dietary preference", ["None", "Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Keto", "Halal"])
    extra_req = st.text_area("Extra requests (e.g., quick, kid-friendly, no nuts, one-pot)", max_chars=200, height=60)
    regenerate = st.checkbox("Enable Regenerate button")
    use_cli_fallback = st.checkbox("Use CLI fallback if API fails")
    submitted = st.form_submit_button("Generate Recipe")

# ---------------- Recipe Generation ----------------
def generate_recipe():
    prompt = build_prompt(
        recipe_name.strip(),
        cuisine or None,
        int(servings),
        None if dietary=="None" else dietary,
        extra_req or None
    )
    
    with st.spinner("Chatbot is working on it ... just wait a while"):
        result = call_gemini(prompt)
        if "Gemini API Error" in result and use_cli_fallback:
            import subprocess
            try:
                cmd = f'gemini chat "{prompt}"'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                result = res.stdout if res.stdout else res.stderr
            except Exception as e:
                result = f"CLI fallback failed: {e}"

    # Generate image dynamically
    image = generate_image(recipe_name)
    
    # Save in history
    st.session_state.history.insert(0, {
        "name": recipe_name,
        "prompt": prompt,
        "response": result,
        "image": image,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    })

# ---------------- Submit ----------------
if submitted:
    if not recipe_name.strip():
        st.error("First enter recipe name 😊")
    else:
        generate_recipe()
        st.success("Recipe generated! Scroll below to view.")

# ---------------- Display Last Recipe ----------------
if st.session_state.history:
    last = st.session_state.history[0]
    st.markdown("---")
    st.subheader(f"Recipe: {last['name']}")
    st.caption(f"Generated at: {last['time']}")
    
    # Show image
    st.image(last["image"], caption=f"{last['name']}", use_column_width=True)
    
    # Show recipe text
    st.markdown(last["response"])
    
    # Download button
    st.download_button(
        "Download recipe (.txt)",
        last["response"],
        file_name=f"{last['name'].replace(' ','_')}_recipe.txt"
    )
    
    # Regenerate button
    if regenerate:
        if st.button("Regenerate Recipe"):
            generate_recipe()
            st.experimental_rerun()

# ---------------- History Section ----------------
if st.session_state.history:
    with st.expander("History — recent recipes"):
        for idx, item in enumerate(st.session_state.history):
            st.write(f"**{idx+1}. {item['name']}** — {item['time']}")
            if st.button(f"Show {idx+1}", key=f"show_{idx}"):
                st.image(item["image"], caption=f"{item['name']}", use_column_width=True)
                st.markdown(item["response"])
            st.markdown("---")


