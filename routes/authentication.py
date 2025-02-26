from flask import Blueprint, request, url_for, jsonify
from flask_api import status
from models.main import *
from models.appendix import *
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, get_jwt_identity, get_jwt)
from config import Config

app_auth = Blueprint('app_auth',__name__)

@app_auth.route("/authenticate", methods=['POST'])
def auth():
    data = request.get_json()

    email = data.get('email', None)
    password = data.get('password', None)

    user = User.authenticate(email, password)

    if user is None:
        return {
            'status': 'error',
            'message': 'Usuário inválido',
        }, status.HTTP_401_UNAUTHORIZED
    else:
        claims = {
            'schema': user.schema,
            'config': user.config
        }
        access_token = create_access_token(identity=user.id,additional_claims=claims)
        refresh_token = create_refresh_token(identity=user.id,additional_claims=claims)

        notification = Notify.getNotification(schema=user.schema)

        if notification is not None:
            db_session = db.create_scoped_session()
            db_session.connection(execution_options={'schema_translate_map': {None: user.schema}})

            notificationMemory = db_session.query(Memory)\
              .filter(Memory.kind == 'info-alert-' + str(notification['id']) + '-' + str(user.id))\
              .first()
              
            if notificationMemory is not None:
                notification = None
        

        return {
            'status': 'success',
            'userName': user.name,
            'userId': user.id,
            'email': user.email,
            'schema': user.schema,
            'roles': user.config['roles'] if user.config and 'roles' in user.config else [],
            'nameUrl': Memory.getNameUrl(user.schema)['value'] if user.permission() else 'http://localhost/{idPatient}',
            'notify': notification,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'apiKey': Config.API_KEY if hasattr(Config, 'API_KEY') else ''
        }, status.HTTP_200_OK


@app_auth.route("/refresh-token", methods=['POST'])
@jwt_required(refresh=True)
def refreshToken():
    current_user = get_jwt_identity()
    current_claims = get_jwt()
    
    if 'schema' in current_claims:
        claims = {
            "schema": current_claims['schema'],
            "config": current_claims['config']
        }        
    else:
        db_session = db.create_scoped_session()
        user = db_session.query(User).filter(User.id == current_user).first()
        claims = {
            "schema": user.schema,
            "config": user.config
        } 

    access_token = create_access_token(identity=current_user,additional_claims=claims)
    return {'access_token': access_token}