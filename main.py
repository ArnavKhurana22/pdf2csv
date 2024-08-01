import streamlit as st
import pytesseract
from PIL import Image
import os
from pdf2image import convert_from_bytes
from configparser import ConfigParser
import pathlib
import csv
from io import BytesIO
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up the API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    st.error("API key not found. Please check your .env file.")
    st.stop()  # Stop execution if API key is not available

genai.configure(api_key=api_key)

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

# Load configuration
def load_config():
    config = ConfigParser()
    config.read('config.ini')
    popplerLoc = config.get('settings', 'PopplerPath')
    tesseractLoc = config.get('settings', 'TesseractPath')
    return popplerLoc, tesseractLoc

# Get path of source
def get_path_of_source(filename):
    return pathlib.Path(filename)

# Test if paths are correctly loaded
def test_paths():
    popplerLoc, tesseractLoc = load_config()
    st.write(f"Poppler Path: {popplerLoc}")
    st.write(f"Tesseract Path: {tesseractLoc}")

# Step 1: PDF to JPG
def pdf_to_jpg(pdf_bytes, firstpage, lastpage, userpw, popplerLoc):
    images = convert_from_bytes(pdf_bytes, dpi=500, first_page=firstpage, last_page=lastpage, userpw=userpw, poppler_path=popplerLoc)
    jpg_files = []
    for i, image in enumerate(images):
        img_filename = f"page_{i + 1}.jpg"
        image.save(img_filename, 'JPEG')
        jpg_files.append(img_filename)
        st.write(f"Converted to JPG...Saving to: {img_filename}")
    return jpg_files

# Step 2: JPG to TXT
def save_to_file_as_txt(filename, text):
    filenamenew = get_path_of_source(filename).with_suffix('.txt')
    st.write(f"Converted to TXT...Saving to: {filenamenew}")
    with open(filenamenew, 'w') as fout:
        fout.write(text)
    return filenamenew

def jpg_to_txt(tesseractLoc, jpg_files):
    pytesseract.pytesseract.tesseract_cmd = tesseractLoc
    txt_files = []
    for jpg_file in jpg_files:
        img = Image.open(jpg_file)
        text = pytesseract.image_to_string(img)
        txt_file = save_to_file_as_txt(jpg_file, text)
        txt_files.append(txt_file)
    return txt_files

# Step 3: TXT to CSV
def txt_to_csv(txt_files):
    converted_list = []
    for txt_file in txt_files:
        with open(txt_file) as fileToRead:
            lines = fileToRead.readlines()
        for line in lines:
            without_comma = line.replace(",", "")
            with_added_commas = without_comma.replace(" ", ",")
            cleaned_line = with_added_commas.replace("\"", "")
            converted_list.append(cleaned_line)
    return converted_list

def save_as_csv(data, filename):
    filename = get_path_of_source(filename).with_suffix('.csv')
    st.write(f"Converted to CSV...Saving to: {filename}")
    with open(filename, 'w', newline='') as fout:
        fout.writelines(data)  # Write each line in the data list
    return filename

def analyze_csv_with_gemini(csv_content):
    prompt = f"Analyze the following CSV data:\n{csv_content}"
    try:
        # Use the model to generate a response
        response = model.generate_content(prompt=prompt)  # Adjust method and params as needed
        return response.get('text', 'No response text found')
    except TypeError as e:
        st.error(f"TypeError: {e}")
        return "A TypeError occurred."
    except AttributeError as e:
        st.error(f"AttributeError: {e}")
        return "An AttributeError occurred."
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return "An unexpected error occurred."

def main():
    st.title("PDF to CSV Converter")
    st.write("This application converts PDF files to CSV format in three steps:")
    st.write("Step 1: PDF to JPG")
    st.write("Step 2: JPG to TXT")
    st.write("Step 3: TXT to CSV")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file is not None:
        pdf_bytes = uploaded_file.read()
        st.success("File uploaded successfully")
        
        userpw = st.text_input("Password (if any)", type="password")
        first_page = st.number_input("First Page", min_value=1, value=1)
        last_page = st.number_input("Last Page", min_value=1, value=1)
        
        if st.button("Convert"):
            popplerLoc, tesseractLoc = load_config()
            
            jpg_files = pdf_to_jpg(pdf_bytes, first_page, last_page, userpw, popplerLoc)
            txt_files = jpg_to_txt(tesseractLoc, jpg_files)
            csv_data = txt_to_csv(txt_files)
            csv_filename = save_as_csv(csv_data, "output")
            
            st.success("Conversion completed successfully")

            # Display CSV content
            with open(csv_filename, 'r') as file:
                csv_content = file.read()
            
            st.write("CSV Data:")
            st.write(csv_content)  # Display CSV content directly

            # Analyze CSV content with Gemini
            analysis_result = analyze_csv_with_gemini(csv_content)
            st.write("Analysis Result:")
            st.write(analysis_result)

if __name__ == '__main__':
    main()
