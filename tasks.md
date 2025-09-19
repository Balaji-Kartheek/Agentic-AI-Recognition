# TO DO Items

[ ] Create the Data
[ ] Instead os downloading the audio files, use the existing folders scenario wise
[ ] Make 1 more llm which looks into the Current Conversation & accordingly send the audio files
[ ] Generate a report on the results






# Conversation UUIDs

## Current Active UUIDs (Multi-Conversation Mode)
1. 83159ea2a0e9dd03909fbceaa179dbc0 - cancel
2. e2550cc8450d00fa47164d3797bb775c - reschedule  
3. a75f4ec64775686673384db31e43b99e - confirm

## Previous UUIDs (Archived)
- 7d2f577843761d41a6cf290b6702995e
- 854eae75e1851545d5718c382995977a
- 40eb1681a081eec691b67e58d4fb1a4d


 
 # Voice Generation from the Text (TTS)

 1. Google Translate (gTTS)
 2. Edge (Microsot TTS)
 3. pyttsx3
 4. Coqui TTS




 ## Synthetic Voice Run

 1. Create the steps that need to be followed by the user in the conversation
 2. A Text file/ Input which pre as 
 Step 1: Hello, I want to confirm my appointment
 Step 2:
 Step 3:

 ...
 3. Convert only the text [Hello, I want to confirm my appointment] -> voice_1.mp3
 4. All of them store in the dynamic folder
 5. connect with the web socket and same like the first flow where it is sending the voice files followed by the agent response, but in this we are downloading the voice files from the conversation uuids but in this will generate the voice files
 6. continue the same steps



 Need to check
1. Change the Evaluation mechanism for the Dynamic Voice Generation -> to use the generated transcript only
2. For Generation of Lastname, 






### Human vs Synthetic Execution

1. Get the Config
2. Human voice
3. All the Details Input
4. Run Status
- progress run
- Start Backgorunf run
- Clear the app, Converation.logs
- _worker()
- Run Evaluator
- AvaamoAudioEvaluator - app.py
- Process the Conversations
    - Create WebSocket
    - Fetch the Conversations
    - Clear the Existing Files
    - Check if all downloads were successfull
    - Create the WebSocket
    - Start Pinging
    - Sending the Audio Files
    - send_all_audio_files_sequentially -  audio_service.py
        - Preparing to send 
        - Ensure WebSocket is still Open
        - send_audio_file_and_wait_for_response( step_audio[download_result]['step']['utterance'], response_timeout) - audiO_service.py
        - Send & Wait for the Bot Response
            - Read the Audio File - Voice
            - log the Utterance
            - Wait for the bot_response

    - Stop Pinging






















