import streamlit as st
import pytesseract
from PIL import Image
import os
from pdf2image import convert_from_bytes
from configparser import ConfigParser
import pathlib
import google.generativeai as genai
from dotenv import load_dotenv
import csv

# Load environment variables
load_dotenv()

# Set up the API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    st.error("API key not found. Please check your .env file.")
    st.stop()  # Stop execution if API key is not available

try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}")
    st.stop()

# Initialize the model
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error initializing Gemini model: {e}")
    st.stop()

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

# Step 1: PDF to JPG
def pdf_to_jpg(pdf_bytes, userpw, popplerLoc):
    images = convert_from_bytes(pdf_bytes, dpi=500, userpw=userpw, poppler_path=popplerLoc)
    jpg_files = []
    for i, image in enumerate(images):
        img_filename = f"page_{i + 1}.jpg"
        image.save(img_filename, 'JPEG')
        jpg_files.append(img_filename)
    return jpg_files

# Step 2: JPG to TXT
def save_to_file_as_txt(filename, text):
    filenamenew = get_path_of_source(filename).with_suffix('.txt')
    with open(filenamenew, 'w') as fout:
        fout.write(text)
    return filenamenew

def jpg_to_txt(tesseractLoc, jpg_files, language):
    pytesseract.pytesseract.tesseract_cmd = tesseractLoc
    txt_files = []
    for jpg_file in jpg_files:
        img = Image.open(jpg_file)
        text = pytesseract.image_to_string(img, lang=language)
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
    with open(filename, 'w', newline='') as fout:
        fout.writelines(data)  # Write each line in the data list
    return filename

# Analyze CSV content with Gemini and save the result
def analyze_csv_with_gemini(csv_content, output_filename):
    try:
        # Use the model to generate a response
        response = model.generate_content(f"just convert the text errors and display it in csv\n{csv_content}")
        
        # Access the response text correctly based on the actual structure
        response_text = response.text if hasattr(response, 'text') else 'No response text found'
        
        st.write(response_text)  # Print the response text
        
        # Save the response text as CSV
        with open(output_filename, 'w') as fout:
            fout.write(response_text)
        
        st.write(f"Saved Gemini analysis to CSV: {output_filename}")
        return output_filename
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
    st.write("This application converts PDF files to CSV format in three steps, extracting various types of customer and shop details, including those indicated by tick marks, cross marks, or shaded boxes.")
    st.write("Step 1: PDF to JPG")
    st.write("Step 2: JPG to TXT")
    st.write("Step 3: TXT to CSV")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file is not None:
        pdf_bytes = uploaded_file.read()
        st.success("File uploaded successfully")
        
        userpw = st.text_input("Password (if any)", type="password")
        
        language = st.selectbox("Select OCR Language", ["eng", "fra", "msa","deu","spa"])
        
        if st.button("Convert"):
            try:
                with st.spinner('Please wait...'):
                    popplerLoc, tesseractLoc = load_config()
                    
                    jpg_files = pdf_to_jpg(pdf_bytes, userpw, popplerLoc)
                    txt_files = jpg_to_txt(tesseractLoc, jpg_files, language)
                    csv_data = txt_to_csv(txt_files)
                    csv_filename = save_as_csv(csv_data, "output")
                
                st.success("Conversion completed successfully")

                # Analyze CSV content with Gemini
                analysis_csv_filename = get_path_of_source("gemini_analysis_output.csv")
                analyze_csv_with_gemini(csv_data, analysis_csv_filename)
                st.write(f"Analysis saved to: {analysis_csv_filename}")

            except Exception as e:
                st.error(f"An error occurred during conversion: {e}")

if __name__ == '__main__':
    main()