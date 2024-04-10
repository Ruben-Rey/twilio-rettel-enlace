# retell-vide-demo

This is a sample demo repo to show how to have your own LLM plugged into Retell.

## Steps to run in localhost

1. First install dependencies

```bash
pip3 install -r requirements.txt
```

2. Fill out the API keys in `.env`

3. In another bash, use ngrok to expose this port to public network

```bash
ngrok http 8080
```

4. Start the websocket server

```bash
python -m uvicorn server:app --reload --port=8080
```

You should see a fowarding address like
`https://dc14-2601-645-c57f-8670-9986-5662-2c9a-adbd.ngrok-free.app`, and you put on .env

### Phone Call Features via Twilio

The `twilio_server.py` contains helper functions you could utilize to create phone numbers, tie agent to a number,
make a phone call with an agent, etc. Here we assume you already created agent from last step, and have `agent id` ready.

To ues these features, follow these steps:

1. Put your ngrok ip address into `.env`, it would be something like `https://dc14-2601-645-c57f-8670-9986-5662-2c9a-adbd.ngrok-free.app`.

2. (optional) Call `create_phone_number` to get a new number and associate with an agent id. This phone number now can handle inbound calls as long as this server is running.

3. (optional) Call `end_call` to end this on-going call.

4. Call `create_phone_call` to start a call with caller & callee number, and your agent Id. This call would use the agent id supplied, and ignore the agent id you set up in step 3 or 4. It automatically hang up if machine/voicemail/IVR is detected. To turn it off, remove "machineDetection, asyncAmd" params.
