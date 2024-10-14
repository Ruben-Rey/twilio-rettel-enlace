from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
import os
import urllib
from pprint import pprint

load_dotenv()
class TwilioClient:

    def __init__(self):
        # Este Client es la clase principal de la biblioteca de Twilio para Python. Se inicializa con las credenciales de su cuenta Twilio.
        self.client = Client(
            os.environ["TWILIO_ACCOUNT_ID"], os.environ["TWILIO_AUTH_TOKEN"]
        )
        
    # Termina una llamada en curso
    def end_call(self, sid):
        #self.client.calls(sid) accede a la llamada específica usando su SID.
        #update() es un método que permite modificar una llamada en curso.
        try:
            call = self.client.calls(sid).update(
                # Esto es TwiML (Twilio Markup Language), un conjunto de instrucciones XML para Twilio.
                # <Response> es el elemento raíz de TwiML.
                # <Hangup> es una instrucción que le dice a Twilio que termine la llamada.
                
                twiml="<Response><Hangup></Hangup></Response>",
            )
            # vars(call) convierte el objeto call en un diccionario, mostrando todas sus propiedades.
            print(f"Ended call: ", vars(call))
        except Exception as err:
            print(err)

    # Registra un número de teléfono con un agente de Retell.
    def register_phone_agent(self, phone_number, agent_id):
        try:
            phone_number_objects = self.client.incoming_phone_numbers.list(limit=200)
            numbers_sid = ""
            for phone_number_object in phone_number_objects:
                if phone_number_object.phone_number == phone_number:
                    number_sid = phone_number_object.sid
            if number_sid is None:
                print(
                    "Unable to locate this number in your Twilio account, is the number you used in BCP 47 format?"
                )
                return
            phone_number_object = self.client.incoming_phone_numbers(number_sid).update(
                voice_url=f"{os.environ['NGROK_IP_ADDRESS']}/twilio-voice-webhook/{agent_id}"
            )
            print("Register phone agent:", vars(phone_number_object))
            return phone_number_object
        except Exception as err:
            print(err)
            
    # Inicia una llamada saliente.
    def create_phone_call(self, from_number, to_number, agent_id, custom_variables):

        #Avoid errors.
        if not isinstance(custom_variables, dict):
            custom_variables = {}

        query_string = urllib.parse.urlencode(custom_variables)
        try:
            call = self.client.calls.create(
                machine_detection="Enable",
                machine_detection_timeout=8,
                async_amd="true",
                async_amd_status_callback=f"{os.getenv('NGROK_IP_ADDRESS')}/twilio-voice-webhook/{agent_id}",
                url=f"{os.environ['NGROK_IP_ADDRESS']}/twilio-voice-webhook/{agent_id}?{query_string}",
                to=to_number,
                from_=from_number,
                status_callback=f"{os.environ['STATUS_URL']}",
                status_callback_event=["completed"]
            )
            print(f"Call from: {from_number} to: {to_number}")
            return call
        except Exception as err:
            print(err)

    # Obtiene el estado de una llamada.
    def get_call_status(self, call_id):
        #calls es un recurso que representa todas las llamadas en su cuenta Twilio.
        #Al pasar call_id a calls(), estamos seleccionando una llamada específica.
        call_status = self.client.calls(call_id).fetch()
        # fetch() es un método que hace una solicitud HTTP GET al API de Twilio para obtener los detalles de esa llamada específica.
        return call_status
    
    # Actualiza una llamada en curso.
    def update_call(self, call_id, item):
        updated_call = self.client.calls(call_id).update(twiml=item)
        pprint(updated_call)
        return updated_call

    def fetch(self, call_sid):
        return self.client.calls(call_sid).fetch()


