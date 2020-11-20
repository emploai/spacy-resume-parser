import json

from flask import request, abort
from flask_restful import Resource

from controller.utils.parser import ResumeParser

class resumeController(Resource):
  '''
  Main Resume Parser POST request 
  ''' 
  def post(self):
    json_data = request.json
    localpath = json_data['path']

    if localpath is not None:
      resume = ResumeParser(localpath, None, None)
      resumeJSON = resume.get_extracted_data()
      return(resumeJSON)
    else:
      return abort(400,  'path input is required')

