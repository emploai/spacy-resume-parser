from flask import Flask
from flask_restful import Api
from controller import resumeController

application = Flask(__name__)
api = Api(application)

api.add_resource(resumeController.resumeController, '/resume/parse')

if __name__ == '__main__':
  application.run(port=7000, debug=False)