import os
from flask import Flask, request, render_template, redirect, url_for
import fitz
import hashlib
import docx
from itertools import combinations

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Function to read content from DOCX
def read_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return ' '.join(full_text)

# Function to read content from PDF
def read_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Function to read the content of both DOCX and PDF
def read_document(file_path):
    if file_path.endswith('.docx'):
        return read_docx(file_path)
    elif file_path.endswith('.pdf'):
        return read_pdf(file_path)
    else:
        return ""

def get_shingles(doc, shingle_size=5):
    words = doc.split()
    shingles = [' '.join(words[i:i + shingle_size]) for i in range(len(words) - shingle_size + 1)]
    return shingles


def hash_shingle(shingle):
    return hashlib.sha256(shingle.encode()).hexdigest()

def get_hashed_shingles(doc, shingle_sizes=5):
    shingles = get_shingles(doc, shingle_sizes)
    hashed_shingles = set(hash_shingle(shingle) for shingle in shingles)
    return hashed_shingles

def jaccard_similarity(set1, set2):
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0

results_cache = []


@app.route("/", methods=['GET', 'POST'])
def index():
    global results_cache
    if request.method == 'POST':
        uploaded_files = request.files.getlist("docs[]")
        file_paths = []

        for doc in uploaded_files:
            if doc:
                doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
                doc.save(doc_path)
                file_paths.append(doc_path)

        docs_hashed_shingles = {}
        for file_path in file_paths:
            doc_content = read_document(file_path)
            docs_hashed_shingles[file_path] = get_hashed_shingles(doc_content)

        results_cache = []
        for (file1, shingles1), (file2, shingles2) in combinations(docs_hashed_shingles.items(), 2):
            similarity = jaccard_similarity(shingles1, shingles2)
            similarity_percentage = similarity * 100
            results_cache.append({
                'file1': os.path.basename(file1),
                'file2': os.path.basename(file2),
                'similarity': similarity_percentage
            })

        # Sort results by similarity in descending order
        results_cache.sort(key=lambda x: x['similarity'], reverse=True)

        # Delete files only after processing
        for file_path in file_paths:
            os.remove(file_path)

    # Filter results with similarity > 80%
    filtered_results = [result for result in results_cache if result['similarity'] > 80]

    return render_template('index.html', results=filtered_results)

@app.route("/sociogram", methods=['GET'])
def sociogram():
    global results_cache
    print("Results Cache:", results_cache)  # Debugging: Check what data is being sent
    return render_template('sociogram.html', results=results_cache)

if __name__ == "__main__":
    app.run(debug=True)