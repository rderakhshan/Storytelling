import os
import re
import io
import requests
from base64 import b64decode
from PIL import Image
from prompts import image_gen_system_prompt
import anthropic
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
STABILITY_API_KEY = os.environ['STABILITY_API_KEY']

CLIENT = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def gen_image(prompt, height=1024, width=1024, num_samples=1):
    response = requests.post(
        "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {STABILITY_API_KEY}"
        },
        json={
            "text_prompts": [
                {
                    "text": prompt,
                }
            ],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": num_samples,
            "steps": 30,
        },
    )

    data = response.json()
    return data['artifacts'][0]['base64']

def save_image(b64_string, filename):
    image_data = b64decode(b64_string)
    image = Image.open(io.BytesIO(image_data))
    image.save(filename)
    print(f"Image saved as {filename}")

# image = gen_image('Futuristic City')
# save_image(image, 'future.png')

def illustrator_claude(prompt):
    claude_response = CLIENT.messages.create(
        system=image_gen_system_prompt,
        model='claude-3-5-sonnet-20240620',
        max_tokens=1024,
        messages=[
          {"role": "user", "content": prompt}
        ],
    ).content[0].text
    return claude_response
    
# print(illustrator_claude('Write the first page of a 5-page story.'))

def parse_response_and_gen_image(claude_response):
    if "<function_call>" in claude_response:
        image_prompt = claude_response.split('<function_call>create_image(')[1].split(')</function_call>')[0].replace('"', '')
    else:
        image_prompt = None

    function_free_claude_response = re.sub(r'<function_call>.*</function_call>', '', claude_response)
    return (function_free_claude_response, image_prompt)

def generate_story_pages(num_pages):
    pages = []
    for i in range(num_pages):
        if i == 0:
            prompt = f"""
                Write the first page of a 5-page bedtime story (~60 words). No comments. Output only the story.
            """
        elif i == num_pages - 1:
            prompt = f"""
                Write the final page (page {i+1}) of the bedtime story (~60 words). No comments. Output only the story.
                Context so far: {pages}
            """
        else:
            prompt = f"""
                Continue the bedtime story with page {i+1} (~60 words). No comments. Output only the story.
                Context so far: {pages}
            """

        claude_response = illustrator_claude(prompt)
        text, image_prompt = parse_response_and_gen_image(claude_response)
        pages.append((text, image_prompt))

    return pages

def create_pdf(pages, output_filename):
    c = canvas.Canvas(output_filename, pagesize=letter)
    width, height = letter
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        name='CustomStyle',
        parent=styles['Normal'],
        fontName='Helvetica',  # Change to 'ComicSans' if Comic Sans is available
        fontSize=15,  # Set font size to 15
        leading=20,  # Increase line spacing for better readability
        alignment=TA_JUSTIFY
    )

    for text, image_prompt in pages:
        # Generate and add image
        image_base64 = gen_image(image_prompt)
        img = Image.open(io.BytesIO(b64decode(image_base64)))
        c.drawImage(ImageReader(img), 50, height - 450, width=500, height=400)

        # Add text with custom styling
        p = Paragraph(text, style)
        frame = Frame(50, -100, 500, 400, showBoundary=0)
        frame.addFromList([p], c)

        c.showPage()  # Move to a new page for the next content

    c.save()

pages = generate_story_pages(3)
create_pdf(pages, 'story.pdf')