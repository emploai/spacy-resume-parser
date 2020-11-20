python3 -m venv venv

python3 -m spacy download en_core_web_sm

curl -X POST http://localhost:7000/resume/parse -H "Content-Type: application/json" -d "{\"path\": \"/work/github/spaCy-resume-parser/docx/DemoResume.docx\"}" | python -m json.tool
