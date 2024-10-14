import os
import urllib
import httpx
import asyncio
import urllib.parse
from retell import Retell
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from app.twilio_server import TwilioClient
from app.webhook import router as webhook_router
from app.analizer import router as analizer
from twilio.twiml.voice_response import VoiceResponse
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel


app = FastAPI()
twilio_client = TwilioClient()
retell = Retell(api_key= os.getenv('RETELL_API_KEY'))


#Mofify the phone number for inbound calls.
twilio_client.register_phone_agent(os.getenv("PHONE_NUMBER"), os.getenv('RETELL_AGENT_ID'))

load_dotenv(override=True)

#Routers
app.include_router(webhook_router)
app.include_router(analizer)

# Ruta para llamadas salientes:
@app.post("/outbound-call")
async def handle_twilio_voice_webhook(request: Request):
    body = await request.json()
    to_number = body.get('to_number')
    custom_variables = body.get('custom_variables', None)
    call = twilio_client.create_phone_call(os.getenv("PHONE_NUMBER"), to_number, os.environ['RETELL_AGENT_ID'], custom_variables)#from,to
    return {"call_sid": call.sid, "msg": "done"}

# Ruta para el estado de la llamada:
@app.post("/call-status")
async def handle_status_callback(request: Request):
   body = await request.json()
   call_sid = body.get("call_sid")
   call = twilio_client.get_call_status(call_sid)
   return {
        "sid": call.sid,
        "duration": call.duration,
        "status": call.status,
        "direction": call.direction,
        "from": call.from_formatted,
        "to": call.to_formatted,
        "start_time": call.start_time,
        "end_time": call.end_time,
    }



class Item(BaseModel):
    phone: str


async def send_data(url ,item: Item):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, json=item.model_dump()
        )
        if response.status_code not in range(200, 300):
            raise HTTPException(
                status_code=response.status_code, detail="Error calling external API"
            )
        return response.json()


# Ruta principal para el webhook de voz de Twilio:
@app.post("/twilio-voice-webhook/{agent_id_path}")
async def handle_twilio_voice_webhook(request: Request, agent_id_path: str):

    #Extrae los parametros de la consulta de la solicitud
    query_params = request.query_params
    
    #Crea un diccionario "custom_variables" con estos parametros
    custom_variables = {key: query_params[key] for key in query_params}

    try:
        # Check if it is machine
        
        #Espera y obtiene los datos del formulario POST enviados por Twilio.
        post_data = await request.form()
        
        #Verifica si la llamada fue contestada por una máquina (contestador automático).
        if "AnsweredBy" in post_data and post_data["AnsweredBy"] == "machine_start":
            #Si es machine
            #Obtiene el estado de la llamada de Twilio usando el CallSid.
            call = twilio_client.get_call_status(post_data["CallSid"])
            
            url = os.getenv("GHL_VOICE_MAIL_URL")
            #Valida si hay una url
            if url is not None and len(url) != 0:
                #Funcion permite crear una tarea asyncrona que se ejecutara concurrentemente
                #Significa que "create_task" se ejecutara en segundo plano, permitiendo que el resto de codigo continue
                asyncio.create_task(
                    #Aqui se instancia directamente, es similar a lo que se hacia antes:
                    #telefono = Item(phone="+514156446")
                    #send_data( os.getenv("GHL_VOICE_MAIL_URL"),telefono))
                    send_data(os.getenv("GHL_VOICE_MAIL_URL"),Item(phone=call.to))
                )
            #Se termina la llamada
            twilio_client.end_call(post_data["CallSid"])
            #Se devuelve una respuesta de texto plano vacìa
            return PlainTextResponse("")
        elif "AnsweredBy" in post_data:
            return PlainTextResponse("")

        #Si no es una constestadora y tampoco tiene el "AnsweredBy" en los datos POST, quiere decir 
        #que una persona contesto
        url = os.getenv("GHL_VOICE_MAIL_URL")
        if url is not None and len(url) != 0:
            asyncio.create_task(
                    send_data(os.getenv("GHL_REMOVE_VOICE_MAIL_URL"),Item(phone=post_data["To"]))
            )
        #Registra la llamada con Retell, configurando los parámetros necesarios.
        call_response = retell.call.register(
            agent_id=agent_id_path,
            audio_websocket_protocol="twilio",
            audio_encoding="mulaw",
            sample_rate=8000,  # Sample rate has to be 8000 for Twilio
            from_number=post_data["From"],
            to_number=post_data["To"],
            retell_llm_dynamic_variables=custom_variables,
            metadata={"twilio_call_sid": post_data["CallSid"]},
        )
        
        
        # Esto crea un nuevo objeto VoiceResponse. Este objeto se utiliza para construir una respuesta TwiML (Twilio Markup Language),
        # que es un conjunto de instrucciones XML que le dice a Twilio cómo manejar una llamada.
        response = VoiceResponse()
        
        # El método connect() inicia un elemento <Connect> en el TwiML. Este elemento se usa para conectar la llamada a otro servicio o endpoint.
        start = response.connect()
        
        # El método stream() añade un elemento <Stream> dentro del <Connect>.
        # Esto le dice a Twilio que transmita el audio de la llamada a la URL especificada, que en este caso es un WebSocket de Retell.
        # La URL incluye el call_response.call_id, que es un identificador único para esta llamada en el sistema de Retell.
        start.stream(
            url=f"wss://api.retellai.com/audio-websocket/{call_response.call_id}"
        )
        return PlainTextResponse(str(response), media_type="text/xml")
    except Exception as err:
        print(f"Error in twilio voice webhook: {err}")
        return JSONResponse(
            status_code=500, content={"message": "Internal Server Error"}
        )
