#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource
from marshmallow import Schema, fields, ValidationError
import configparser

app = Flask(__name__)
api = Api(app)
db = SQLAlchemy(app)
config = configparser.ConfigParser()
config.read('config.ini')
access_information = config['access_information']
# DB接続情報の作成（情報変更はconfig.iniファイルから）
db_url = access_information['dialect'] + "+" \
         + access_information['driver'] + "://" \
         + access_information['username'] + ":" \
         + access_information['password'] + "@" \
         + access_information['host'] + "/" \
         + access_information['database'] + "?charset="\
         + access_information['charset_type']
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
# JSONでの日本語文字化け対策
app.config['JSON_AS_ASCII'] = False


# MODELS

class Table(db.Model):
    __tablename__ = 'Sample'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    status = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.now)

    def __repr__(self):
        return '%s %s %s' % (self.id, self.status, self.created_at)


# Schemas
# Custom validator
def must_not_be_blank(data):
    if not data:
        raise ValidationError('Data not provided.')


class CommonSchema(Schema):
    trackingRecordId = fields.Int()
    trackingRecordStatus = fields.Str(required=True, validate=must_not_be_blank,
                                      error_messages={'required': 'trackingRecordStatus is required.'})
    created_at = fields.DateTime(attribute="created_at")


statuses_schema = CommonSchema(many=True)


# API
class Common(Resource):
    def get(self):
        if request.headers['Content-Type'] != 'application/json':
            data = Response(406, 'Not Acceptable', 'Content-Type', '')
            return data.error()

        status = Table.query.all()
        result = CommonSchema.dump(status, many=True)
        return jsonify({
            'result': result,
            'status_code': 201
        })

    def post(self):
        if request.headers['Content-Type'] != 'application/json':
            data = Response(406, 'Not Acceptable', 'Content-Type', '')
            return data.error()

        try:
            json_data = request.get_json()  # POSTされたJSONを取得
        except:
            data = Response(415, 'Unsupported Media Type', 'JSON Error', '')
            return data.error()

        try:
            CommonSchema(strict=True).load(json_data)
        except ValidationError as err:
            data = Response(400, 'Bad Request', err.messages, '')
            return data.error()

        # Create new quote
        try:
            status = Table(status=json_data['trackingRecordStatus'])
            db.session.add(status)
            db.session.commit()
        except Exception as key_err:
            data = Response(415, 'Could not insert data', str(key_err), json_data)
            return data.error()

        return Response.success(self)


# Response
class Response:
    def __init__(self, error_Code, errorMessage, developerMessage, errorData):
        self.error_Code = error_Code
        self.errorMessage = errorMessage
        self.developerMessage = developerMessage
        self.errorData = errorData

    def success(self):
        return jsonify({
            'Content-Type': 'application/json'
        },
            {
                'Message': 'Created new status.',
                'status_Code': 201
            })

    def error(self):
        with open('log.txt', mode='a', encoding='utf-8') as log:
            log.write('\n' + str(self.errorData))

        return jsonify({'error_Code': self.error_Code,
                        'errorMessage': self.errorMessage,
                        'developerMessage': self.developerMessage})


api.add_resource(Common, '/performanceManagement/v1/common')