# Spacy Based Resume Parser
This server is based on spaCy. It is used to train a custom model, which the parser uses to extract data. The data is then displayed in a JSON format.
As of right now, there's a demo document that the parser is able to accurately pull data from. Please do check it out. Further work will be done such that the parser is able to accurately extract data regardless of the resume format and also be able to pull data from tables, boxes, etc. 

## Setup
These steps are to setup and run the parser on Ubuntu.
### Virtual Environment Setup
Firstly, ensure that you're using Python 3.6 and up and that you have pip setup.
To create a virtual environment using the terminal,
```
python3 -m venv venv
```
Activate the virtual environment by using,
```
source venv/bin/activate
```
Once inside the virtual environment, install the dependencies using,
```
pip install -r requirements.txt
```
And finally, install the small spaCy english model by,
```
python3 -m spacy download en_core_web_sm
```
Inorder to deactivate the Virtual Environment, you can do so by,
```
deactivate
```

### Install Textract
To install Textract, we need to first install some system packages using,
```
apt-get install python-dev libxml2-dev libxslt1-dev antiword unrtf poppler-utils pstotext tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev swig
```
Then we need to activate our virtual environment again, and then,
```
pip install textract
```

### Train the Models
Model building is still a work in progress but a basic custom model can be trained. While inside the virtual environment, it can be trained by,
```
python training/trainer.py
```
It will create the necessary files for the parser to run in the ```models``` directory.

## Using the Parser
While inside the virtual environment, the server can be started by,
```
python server.py
```
In another terminal window, using curl, we will define our post request by,
```
curl -X POST http://localhost:7000/resume/parse -H "Content-Type: application/json" -d "{\"path\": \"/path/to/your/file/\"}" | python -m json.tool
```
After doing so, you should see what the parser was able to detect in JSON form.

