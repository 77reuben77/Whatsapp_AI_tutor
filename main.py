import requests
import openai
import ast
import os
from google.cloud import vision
from datetime import datetime
from google.cloud import vision_v1 as vision
from flask import Flask, request, jsonify
import mimetypes
import sqlalchemy
from sqlalchemy import text


class GoogleVisionAPI:
    def __init__(self, credentials_path="mysecondproject-384809-e3169e916978.json"):
        self.client = vision.ImageAnnotatorClient.from_service_account_json(credentials_path)

    def ocr_image(self, image_path):
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            return texts[0].description
        else:
            return ''


class WhatsAppGraphAPI:
    def __init__(self, phone_number):
        self.phone_number = phone_number

        self.page_access_token = os.environ.get('PAGE_ACCESS_TOKEN')
        print(f'Page Access Token: {self.page_access_token}')

        self.base_url = self.base_url = f'https://graph.facebook.com/v16.0/107551035667608' \
                                        f'/messages?access_token={self.page_access_token} '

    def get_whatsapp_account_info(self):
        url = 'https://graph.facebook.com/v16.0/107551035667608'
        headers = {'Authorization': f'Bearer {self.page_access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f'Error retrieving WhatsApp account info: {response.status_code} {response.text}')
            else:
                print(f'Retrieved WhatsApp account info: {response.json()}')
        except Exception as e:
            print(f"Error: {e}")

    def send_text_message(self, message):
        payload = {
            'messaging_product': 'whatsapp',
            'to': self.phone_number,
            'type': 'text',
            'text': {
                'body': message
            }
        }

        try:
            response = requests.post(self.base_url, json=payload)

            if response.status_code != 200:
                print(f'Error sending message: {response.status_code} {response.text}')
        except Exception as e:
            print(f"Error: {e}")

    def send_template_message(self, template_name, template_parameters):
        payload = {
            'recipient': {'phone_number': self.phone_number},
            'message': {
                'attachment': {
                    'type': 'template',
                    'payload': {
                        'template_type': 'button',
                        'text': template_name,
                        'buttons': [template_parameters],
                    },
                },
            },
            'messaging_type': 'MESSAGE_TAG',
            'tag': 'ACCOUNT_UPDATE',
        }

        try:
            response = requests.post(self.base_url, json=payload)

            if response.status_code != 200:
                print(f'Error sending message: {response.status_code} {response.text}')
        except Exception as e:
            print(f"Error: {e}")

    def download_media(self, media_id, media_type, file_name):
        media_endpoint = f'https://graph.facebook.com/v16.0/{media_id}'
        headers = {'Authorization': f'Bearer {self.page_access_token}'}
        response = requests.get(media_endpoint, headers=headers)

        json_response = response.json()
        media_url = json_response["url"]
        print(media_url)

        response = requests.get(media_url, headers=headers)
        

        if response.status_code == 200:
            content_type = response.headers['content-type']
            print(str(content_type))
            print(str(response.content))
            file_extension = mimetypes.guess_extension(content_type)
            # file_path = f"{file_name}.{}"
            file_path = "/tmp/{}.{}".format(file_name, file_extension)
            print("file path"+ file_path)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
        elif response.status_code == 404:
            print('Media not found. Please try to retrieve a new media URL and download it again.')
        else:
            print(f'Error downloading media: {response.status_code} {response.text}')


class Database:
    # restructure database users and sessions
    # possibly add messages table or delete messages table functions
    def __init__(self, phone_number, message):
        self.engine = connect_unix_socket()
        try:
            self.conn = self.engine.connect()
        except Exception as e:
            print("An error occurred:", e)
            print(traceback.format_exc())
            # return jsonify({'error': 'An error occurred'}), 500
        self.create_tables()
        self.phone_number = phone_number
        self.message = message

    def create_tables(self):
        with self.engine.begin() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS user
                            (id INT AUTO_INCREMENT PRIMARY KEY,
                             name VARCHAR(255), age INT, grade INT, curriculum VARCHAR(255),
                            phone_number VARCHAR(255), parent_phone VARCHAR(255), parent_name VARCHAR(255)
                            ,payment_status INT)
                            ''')

            conn.execute('''CREATE TABLE IF NOT EXISTS sessions
            (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT,
            start_time TIMESTAMP, end_time TIMESTAMP, event VARCHAR(255),
            state VARCHAR(255), previous_message_context LONGTEXT, previous_message_received LONGTEXT,
            current_sum VARCHAR(255), sum_counter INT, right_list VARCHAR(255),
            current_topic_list LONGTEXT, current_topic VARCHAR(255), current_topic_counter INT,
            FOREIGN KEY (user_id) REFERENCES user (id))''')

            conn.execute('''CREATE TABLE IF NOT EXISTS topic (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT,
            session_id INT,
            topic_name VARCHAR(255), topic_sums_attempted INT, percentage INT,
            FOREIGN KEY (user_id) REFERENCES user (id),
            FOREIGN KEY (session_id) REFERENCES sessions (id))''')

            conn.execute('''CREATE TABLE IF NOT EXISTS message
                                (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, session_id INT, role VARCHAR(255),
                                content LONGTEXT, timestamp VARCHAR(255),
                                FOREIGN KEY (user_id) REFERENCES user (id),
                                FOREIGN KEY (session_id) REFERENCES sessions (id))''')

    def add_column(self, table_name, column_name, column_type):
        with self.engine.begin() as conn:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def add_user(self, name, age, grade, curriculum, phone_number, parent_phone, parent_name):
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO user (name, age, grade, curriculum, phone_number, parent_phone, parent_name) VALUES (:name, :age, :grade, :curriculum, :phone_number, :parent_phone, :parent_name)"),
                {"name": name, "age": age, "grade": grade, "curriculum": curriculum, "phone_number": phone_number, "parent_phone": parent_phone, "parent_name": parent_name}
            )

    def get_user_field(self, field):
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT {field} FROM user WHERE phone_number = :phone_number"),
                                  {"phone_number": self.phone_number})
            row = result.fetchone()
            return row[0] if row else None

    def set_user_field(self, field, value):
        with self.engine.begin() as conn:
            try:
                conn.execute(text(f"UPDATE user SET {field} = :value WHERE phone_number = :phone_number"),
                             {"value": value, "phone_number": self.phone_number})
            except Exception as e:
                print(f"Error: {e}")

    def set_user_state(self, state):
        user_id = self.get_user_id()
        session_id = self.get_latest_session_id()
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE sessions SET state = :state WHERE id = :session_id"),
                         {"state": state, "session_id": session_id})

    def set_session_field(self, field, value):
        user_id = self.get_user_id()
        session_id = self.get_latest_session_id()
        with self.engine.begin() as conn:
            try:
                conn.execute(text(f"UPDATE sessions SET {field} = :value WHERE id = :session_id"),
                             {"value": value, "session_id": session_id})
            except Exception as e:
                print(f"Error: {e}")

    def set_user_current_topic(self, current_topic):
        user_id = self.get_user_id()
        session_id = self.get_latest_session_id()
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE sessions SET current_topic = :current_topic WHERE id = :session_id"),
                         {"current_topic": current_topic, "session_id": session_id})


    def get_user(self):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM user WHERE phone_number = :phone_number"), {"phone_number": self.phone_number})
            row = result.fetchone()
            return row[0], row[1], row[2] if row else None

    def get_user_id(self):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT id FROM user WHERE phone_number = :phone_number"), {"phone_number": self.phone_number})
            row = result.fetchone()
            return row[0] if row else None

    def get_topics(self, session_id):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM topic WHERE session_id = :session_id"), {"session_id": session_id})
            return result.fetchall()

    def add_session(self, user_id, event='', end_time=None, state='INITIAL'):
        current_timestamp = datetime.now().isoformat()
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO sessions (user_id, start_time, end_time, state, event, sum_counter, right_list,"
                              "current_topic_counter, current_sum) "
                              "VALUES (:user_id, :start_time, :end_time, :state, :event, :sum_counter, :right_list, :current_topic_counter, :current_sum)"),
                         {"user_id": user_id, "start_time": current_timestamp, "end_time": end_time, "state": state, "event": event, "sum_counter": 0, "right_list": "00000", "current_topic_counter": 0,  "current_sum": ''}
                         )

    def get_sessions_for_user(self):
        user_id = self.get_user_id()
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM sessions WHERE user_ID = :user_id"), {"user_id": user_id})
            return result.fetchall()

    def get_session_field(self, field):
        user_id = self.get_user_id()
        session_id = self.get_latest_session_id()
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT {field} FROM sessions WHERE id = :session_id"), {"session_id": session_id})
            row = result.fetchone()
            return row[0] if row else None

    def get_latest_session_id(self):
        user_id = self.get_user_id()
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT id FROM sessions WHERE User_ID = :user_id ORDER BY start_time DESC LIMIT 1"), {"user_id": user_id})
            row = result.fetchone()
            return row[0] if row else None


    def update_session_end_time(self, session_id):
        current_timestamp = datetime.now().isoformat()
        with self.engine.connect() as conn:
            conn.execute(text("UPDATE sessions SET end_time = :end_time WHERE id = :session_id"), {"end_time": current_timestamp, "session_id": session_id})

    def add_message(self, user_id, session_id, role, content):
        with self.engine.connect() as conn:
            conn.execute(text("INSERT INTO message (user_id, session_id, role, content) VALUES (:user_id, :session_id, :role, :content)"),
                          {"user_id": user_id, "session_id": session_id, "role": role, "content": content})

    def get_messages_for_session(self, session_id):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM message WHERE session_id = :session_id"), {"session_id": session_id})
            return result.fetchall()

    def get_topics_field(self, field):
        user_id = self.get_user_id()
        session_id = self.get_latest_session_id()
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT {field} FROM topic WHERE session_id = :session_id"), {"session_id": session_id})
            row = result.fetchone()
            return row[0] if row else None

    def set_topics_field(self, field, value):
        user_id = self.get_user_id()
        session_id = self.get_latest_session_id()
        with self.engine.connect() as conn:
            try:
                conn.execute(text(f"UPDATE topic SET {field} = :value WHERE session_id = :session_id"), {"value": value, "session_id": session_id})
            except Exception as e:
                print(f"Error: {e}")

    def get_or_start_session(self):
        user_id = self.get_user_id()
        if user_id is not None:
            with self.engine.connect() as conn:
                # Check for an ongoing session (no end_time)
                result = conn.execute(text("SELECT * FROM sessions WHERE user_id = :user_id AND end_time IS NULL"), {"user_id": user_id})
                ongoing_session = result.fetchone()
                # If there is no ongoing session, create a new session
                if not ongoing_session:
                    self.add_session(user_id)
                    session_id = self.get_latest_session_id()
                    print("New session created:", session_id)
                else:
                    session_id = ongoing_session[0]
                    print("Ongoing session found:", session_id)
                return session_id
        else:
            return None


    def validate_phone_number(self):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM user WHERE phone_number = :phone_number"), {"phone_number": self.phone_number})
            count = result.fetchone()[0]
            return count > 0

    def validate_payment_status(self):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM user WHERE phone_number = :phone_number AND payment_status = :payment_status"), {"phone_number": self.phone_number, "payment_status": 1})
            count = result.fetchone()[0]
            return count > 0

    def get_current_topic_percentage(self):
        right_list = self.get_session_field("right_list")
        int_value = 0
        for i in range(5):
            int_value = int_value + int(right_list[i])
        percentage = int_value*20
        return percentage

    def next_topic_maybe(self):
        percentage = self.get_current_topic_percentage()
        if self.get_session_field("sum_counter") >= 5 and percentage >= 80:
            with self.engine.connect() as conn:
                topic_counter = self.get_session_field("topic_counter")
                self.set_user_current_topic(
                    ast.literal_eval(self.get_session_field("topic_list"))[topic_counter])
            return True
        else: 
            return False

    def close(self):
        try:
            self.engine.dispose()
        except Exception as e:
            print(f"Error: {e}")



def connect_unix_socket() -> sqlalchemy.engine.base.Engine:
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    unix_socket_path = os.environ["INSTANCE_UNIX_SOCKET"]

    engine = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={"unix_socket": unix_socket_path},
        ),
    )
    return engine


class OpenAIAPI:
    def __init__(self):
        self.api_key = os.environ['OPENAI_API_KEY']  # Assuming you've set the API key as an environment variable
        openai.api_key = self.api_key

    @staticmethod
    def transcribe_audio(audio_path):
        audio_file = open(audio_path, "rb")
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

        return transcript["text"]

    @staticmethod
    def get_completion(prompt, max_tokens=500):
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=max_tokens,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].text.strip()

    @staticmethod
    def get_chat_completion(messages, max_tokens=1000):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            max_tokens=max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content.strip()


class TutoringChatbot:
    def __init__(self, phone_number, message, m_type):
        self.phone_number = phone_number
        self.message = message
        self.m_type = m_type

        self.whatsapp_graph_api = WhatsAppGraphAPI(phone_number)
        self.openai_api = OpenAIAPI()
        self.database = Database(phone_number, message)

        self.database.get_or_start_session()
        self.state = self.database.get_session_field("state")

    def process_message(self):
        print(self.database.get_session_field("state"))
        if not self.database.validate_phone_number():
            print(self.database.phone_number)
            print(self.database.get_user_field("name"))
            self.new_user()
        elif not self.database.validate_payment_status():
            self.database.set_session_field("event", "NP")
            self.database.update_session_end_time(self.database.get_latest_session_id())
            self.whatsapp_graph_api.send_text_message("Your payment has not been processed for this month, please "
                                                      "visit rem-academy.com to ensure your account has been paid to "
                                                      "keep using the service.")

        else:
            if self.message == "0":
                self.database.update_session_end_time(self.database.get_session_field("id"))
                self.database.add_session(self.database.get_user_id())
                self.send_initial_options()
            else:
                state_handlers = {
                    'INITIAL': self.handle_initial_state,
                    'prepare_test': self.handle_prepare_test_state,
                    'practice_module': self.handle_practice_module,
                    'study_topic': self.handle_study_topic,
                    'study_topic_2': self.handle_study_topic_2,
                    'study_topic_3': self.handle_study_topic_3,
                    'study_topic_4': self.handle_study_topic_4,
                    'study_topic_5': self.handle_study_topic_5,
                    'improve_overall': self.handle_improve_overall,
                }

                handler = state_handlers.get(self.state)
                if handler:
                    handler()
                else:
                    print(f"Warning: Unhandled state '{self.state}'")
            # Handle unrecognized input or prompt the user for clarification

    def new_user(self):
        self.whatsapp_graph_api.send_text_message(
            "Hi, welcome to StudyBuddy. Please visit www.rem-academy/studybuddy/signup in order to use our service. Hope to see you soon!")
        # Add all the necessary code to really add a user

    def handle_initial_state(self):
        if self.message == '1':
            self.state = 'prepare_test'
            self.database.set_user_state('prepare_test')
            self.send_prepare_test_instructions()
        elif self.message == '2':
            self.state = 'study_topic'
            self.database.set_user_state('study_topic')
            self.send_select_topic_instructions()
        elif self.message == '3':
            self.state = 'improve_overall'
            self.database.set_user_state('improve_overall')
            self.send_improve_overall_instructions()
        elif self.message == '4':
            self.state = 'homework'
            self.database.set_user_state('homework')
            self.send_homework_instructions()
        else:
            # Handle unrecognized input
            self.whatsapp_graph_api.send_text_message("I didn't understand your choice. Please try again.\n\n "
                                                      "Remember to reply with '0' at any point to return to the main "
                                                      "menu")
            self.send_initial_options()

    def send_initial_options(self):
        # Send a message with the initial options and WhatsApp reply buttons
        message = "Hi my naam is Merwe en ek is hier om jou te help om " \
                  "jou Wiskunde sommer vinnig vinnig te verbeter, " \
                  "Hier is die verkillende dinge waarmee ek kan help. " \
                  "Asseblief kies een en stuur net die nommer van " \
                  "die opsie aan my terug.\n\n1: Wil jy hulp he om voor " \
                  "te berei vir 'n toets?\n2:Wil jy hulp he om 'n" \
                  "spesefieke onderwerk te leer of te bemeester?\n3:Wil jy graag net jou oorbruggende wiskundige " \
                  "vermoe" \
                  " verbeter\n4: Wil jy he ons moet jou huiswerk vir jou doen?"
        self.whatsapp_graph_api.send_text_message(message)

    def send_homework_instructions(self):
        self.whatsapp_graph_api.send_text_message("Nice Try! HAHA, unfortunately we don't do your"
                                                  " homework for you we'll take you back to the main menu")
        self.send_initial_options()

    def send_improve_overall_instructions(self):
        self.whatsapp_graph_api.send_text_message("I'm glad to hear that you want to improve on your overall maths. "
                                                  "To do this we will firstly identify the problem areas in your "
                                                  "foundation of mathematics so we are going to start by giving you "
                                                  "some questions that you should be able to do by now. But don't "
                                                  "worry if you can't that's why you've got me. To help you improve "
                                                  "on your abilities. please say ready if you're happy to move on"
                                                  "\n(0 for main menu)")

    def handle_improve_overall(self):
        if "ready" in self.message.lower() and "not" not in self.message.lower():
            grade = self.database.get_user_field("grade")
            curriculum = self.database.get_user_field("curriculum")
            completion = self.openai_api.get_completion("please list the topics that a grade " + grade +
                                                        "should know at the end of the year in a " + curriculum
                                                        + " school. Please answer only in a python list and name"
                                                          " every topic specifically, for example solving linear"
                                                          " equations, graphing linear equations etc.")
            self.database.set_session_field("topics", completion.strip())
            current_topic = ast.literal_eval(self.database.get_user_field("topics"))[0]
            self.database.set_user_current_topic(current_topic)

            self.database.set_user_state("practice_module")
            self.send_practice_module_instructions()

        else:
            self.whatsapp_graph_api.send_text_message("I don't understand, please reply with 'ready'"
                                                      " or 0 to go back to the main menu")

    def send_practice_module_instructions(self):
        self.whatsapp_graph_api.send_text_message("Great! Now we will send you sums to practice on, "
              "please reply with a photo of your answer to the "
              "problem and include as much working as possible "
              "in the photo (Try to write neatly and do each "
              "problem on a new page so that all your working"
              " can fit into one photo). Here we go!")
        self.database.set_user_state("practice_module")
        self.send_sum()

    def send_sum(self):
        current_topic = self.database.get_session_field("current_topic")
        yes_or_no = self.openai_api.get_completion(prompt="is '" + current_topic + "' a geometry or trigonometry topic."
                                                                                   " Only answer yes or no",
                                                   max_tokens=5)
        print(yes_or_no)
        if "no" in yes_or_no.lower():
            grade = self.database.get_user_field("grade")
            previous_sum = self.database.get_session_field("current_sum")
            if previous_sum == "" or previous_sum== None:
                current_sum = self.openai_api.get_completion(prompt="Generate a question (like a math problem not theoretical) for the following topic (don't include the answer): " +
                                                                current_topic + "\n The sum should be at the "
                                                                                "level of a grade " + str(grade) + "student.")
            else:
                current_sum = self.openai_api.get_completion(prompt="Generate a question (like a math problem not theoretical) for the following topic (don't include the answer): " +
                                                                current_topic + "Make it similar to: "+previous_sum+ "\n The sum should be at the "
                                                                                "level of a grade " + str(grade) + "student.")
                
            
            self.database.set_session_field("current_sum", current_sum)
            annotation = "\n type a message if you need something else or the sum doesn't make sense." \
                         " Otherwise just send through the photo of your answer"
            self.whatsapp_graph_api.send_text_message(current_sum + annotation)
        else:
            topic_counter = self.database.get_session_field("current_topic_counter") + 1
            topic_list = self.database.get_session_field("topic_list")
            if len(ast.literal_eval(topic_list)) > topic_counter:
                self.database.set_session_field("topic_counter", topic_counter)
                self.database.set_user_current_topic(ast.literal_eval(topic_list)[topic_counter])
                self.send_sum()
            else:
                self.whatsapp_graph_api.send_text_message("You have completed all the topics. Now here is the "
                                                          "recommended topics for you to refresh.")
                # Add code to find the topics that was unsuccessful

    def handle_practice_module(self):
        self.database.next_topic_maybe()
        m_text = self.message
        print(m_text)
        current_sum = self.database.get_session_field("current_sum")
        feedback = self.openai_api.get_completion(
                prompt="Is the following a math problem solution to the problem: \n"+ current_sum+"\n and is it correct? \n\n"+m_text+"\n\n"
                       "\n answer only with yes if both requirements are met, or no if either is not met",
                max_tokens=5)
        if "yes" in feedback.lower():
            self.whatsapp_graph_api.send_text_message("Great Job we'll send your next sum")
            self.send_sum()
        else:
            print(feedback)
            feedback = self.openai_api.get_completion(
                prompt="Is the following a math problem solution for the problem:\n" +current_sum +"\n and is it correct? \n\n"+m_text+
                       "\n\n if not explain why",
                max_tokens=200)
            self.whatsapp_graph_api.send_text_message(feedback)


    def send_prepare_test_instructions(self):
        # Send instructions for preparing for a test
        self.whatsapp_graph_api.send_text_message("Awesome! Great to hear that you are"
                                                  " willing to put in some time to increase"
                                                  " those marks! First please tell me what"
                                                  " topics you will be writing on.")

    def handle_prepare_test_state(self):
        if "yes" in self.message.lower():
            self.state = "practice_module"
            self.database.set_user_state("practice_module")
            self.send_practice_module_instructions()
        else:
            completion = self.openai_api.get_completion(
                prompt=(
                            self.message + "\n\n\nFormat the above list of topics into a python list, exclude all "
                                           "topics that are not "
                                           "related to maths, only include the given topics in the list: (don't add "
                                           "any other topics!) "
                                           "\n\n\n"), max_tokens=30)
            print(completion)
            topic_list = ast.literal_eval(completion.strip().strip("math_topics = ").strip())
            if len(topic_list) == 0:
                self.whatsapp_graph_api.send_text_message("I'm sorry, I couldn't understand"
                                                          " that. Please try again.")
                self.send_prepare_test_instructions()
            else:
                self.database.set_session_field("current_topic_list", completion)
                counter = self.database.get_session_field("current_topic_counter")
                self.database.set_user_current_topic(topic_list[counter])
                self.whatsapp_graph_api.send_text_message("Great! Here are the topics you will be "
                                                          "studying: " + str(topic_list) + ", Send Yes to "
                                                                                           "start or send more "
                                                                                           "topics if you would "
                                                                                           "like to update the list")

    def chat_function(self):
        messages = [
            {"role": "system", "content": "You are a mathematics tutor and your job is to simply explain mathematical "
                                          "concepts to students."},
            {"role": "assistant", "content": self.database.get_user_field("previous_message_context")},
            {"role": "user", "content": self.message},
        ]
        completion = self.openai_api.get_chat_completion(messages, max_tokens=70)
        self.database.set_session_field("previous_message_received", self.message)
        self.database.set_session_field("previous_message_context", completion)
        return completion

    def check_answer(self):
        question = self.database.get_user_field("previous_message_context")
        answer = self.message
        yes_or_no = self.openai_api.get_completion(
            "Is '" + answer + "' the correct answer to '" + question + "\n Only reply with a yes or no.", max_tokens=5)
        return 'yes' in yes_or_no.lower()

    def handle_study_topic(self):
        is_topic_correct = \
            self.openai_api.get_completion(self.message + "\n is the above a specified topic of mathematics"
                                                          "for example: 'equations' is not specified enough,"
                                                          "solving linear equations is good.\n"
                                                          "Reply with Yes or No.", max_tokens=5)
        if "yes" in is_topic_correct.lower():
            self.database.set_user_state("study_topic_2")
            self.database.set_user_current_topic(self.message)
            self.send_study_topic_2_instructions()
        else:
            self.whatsapp_graph_api.send_text_message(
                "Could you be a bit more specific please?\n\n ('0' for main menu)")

    def handle_study_topic_2(self):
        if "ready" in self.message.lower() and "not" not in self.message.lower():
            # create database object to store previous message and then get completion for a quizz question
            previous_context = self.database.get_session_field("previous_message_context")
            completion = self.openai_api.get_completion(
                previous_context + "\n This is the previous memorization work you gave the "
                                   "student. Create a question to test their knowledge.")
            self.database.set_user_state("handle_study_topic_3")
            self.database.set_session_field("previous_message_context", completion)
            self.whatsapp_graph_api.send_text_message("Cool let's just quickly give you a quiz then: \n" + completion)
        else:
            self.whatsapp_graph_api.send_text_message("I don't understand, please reply with 'ready'"
                                                      " or 0 to go back to the main menu")

    def handle_study_topic_3(self):
        if self.check_answer():
            self.database.set_user_state("handle_study_topic_4")
            self.whatsapp_graph_api.send_text_message("Good Job!!! Let's move on.\nPlease don't respond "
                                                      "we'll send the next step shortly")
            self.send_study_topic_4_instructions()
        # here would be a good place to add a keeping score function to ask more than one question
        # But for that the AI would have to be prompted to ask how many questions could be asked
        # out of the theory provided
        else:
            self.whatsapp_graph_api.send_text_message("Nope sorry, Try Again!")

    def handle_study_topic_4(self):
        if "ready" in self.message.lower() and "not" not in self.message.lower():
            self.database.set_user_state("handle_study_topic_5")
            self.whatsapp_graph_api.send_text_message("Okay, let's move on.\nPlease don't respond "
                                                      "we'll send the next step shortly")
            self.send_study_topic_5_instructions()
        else:
            completion = self.chat_function()
            self.whatsapp_graph_api.send_text_message(completion + "\n\n Please type ready to "
                                                                   "continue, or keep on chatting"
                                                                   "\n(0 for main menu)")

    def handle_study_topic_5(self):
        if "ready" in self.message.lower() and "not" not in self.message.lower():
            self.database.set_user_state("practice_module")
            self.whatsapp_graph_api.send_text_message("Okay, let's move on.\nPlease don't respond "
                                                      "we'll send the next step shortly")
            self.send_practice_module_instructions()
        else:
            completion = self.chat_function()
            self.whatsapp_graph_api.send_text_message(completion + "\n\n Please type ready to "
                                                                   "continue, or keep on chatting"
                                                                   "\n(0 for main menu)")

    def send_study_topic_2_instructions(self):
        completion = self.openai_api.get_completion(
            self.database.get_session_field("current_topic") + "\n\n for the"
                                                            "above topic"
                                                            "please list "
                                                            "all the "
                                                            "work that "
                                                            "someone "
                                                            "should "
                                                            "have "
                                                            "memorized in "
                                                            "order to "
                                                            "successfully "
                                                            "master the "
                                                            "topic, "
                                                            "for example "
                                                            "any work "
                                                            "with "
                                                            "exponents "
                                                            "the user "
                                                            "should "
                                                            "memorize all "
                                                            "the "
                                                            "applicable "
                                                            "exponent "
                                                            "rules. So for example list all exponent laws if the question is about exponents.")

        self.database.set_session_field('previous_message_context', completion)
        self.whatsapp_graph_api.send_text_message("Cool, I think I can help you with that, lets start with some "
                                                  "work that I'll need you to memorize in order for you to "
                                                  "successfully understand the topic:\n\n Please memorize the following"
                                                  ":\n\n" + completion + "Reply with 'Ready!' when you are ready to "
                                                                         "move forward.")

    def send_study_topic_4_instructions(self):
        current_topic = self.database.get_user_field("current_topic")
        completion = self.openai_api.get_completion("Please provide an overview of how this topic, "
                                                    "" + current_topic + ", can be completed, "
                                                                         "give an "
                                                                         "explanation by analogy and "
                                                                         "then a step by step guide to finding "
                                                                         "the solution"
                                                    )
        self.database.set_session_field("previous_message_context", completion)
        self.whatsapp_graph_api.send_text_message("Alright now here is a nice overview of how you can complete the "
                                                  "topic, please read through it carefully before moving on. \n\n" +
                                                  completion + "\n\nPlease reply with 'ready' when you are ready "
                                                               "to move on,"
                                                               " or simply ask a question if something "
                                                               "doesn't make sense or if you"
                                                               " need further clarification")

    def send_study_topic_5_instructions(self):
        current_topic = self.database.get_user_field("current_topic")
        completion = self.openai_api.get_completion("Please provide an example of a sum in this topic,"
                                                    "" + current_topic + ", show your steps to solving "
                                                                         "it and add explanation after each step"
                                                                         "then leave a line open between each "
                                                                         "step in your answer")
        self.database.set_session_field("previous_message_context", completion)
        self.whatsapp_graph_api.send_text_message("Alright now here is a nice example of a sum in this topic, "
                                                  "please read "
                                                  "through it carefully before moving on. \n\n" + completion +
                                                  "please reply with 'ready' when you are ready to move on, "
                                                  "or simply ask a question if something doesn't make sense or if you"
                                                  " need further clarification.\n (0 for main menu)")

    def send_select_topic_instructions(self):
        # Send instructions for selecting a topic to study
        self.whatsapp_graph_api.send_text_message("Great to hear, I'll do my best to help you "
                                                  "polish off this topic in no time at all! "
                                                  "Please start by sending me the exact topic"
                                                  "you would like to cover, try to be as "
                                                  "specific as possible. (For example: 'solving"
                                                  " linear equations' is good, 'equations' is "
                                                  "too little information)")


def handle_webhook(message_payload):
    message_text = ''
    message_payload = message_payload.get_json()
    print(message_payload)
    entry = message_payload.get("entry")[0]
    changes = entry.get("changes")[0]
    value = changes.get("value")

    if value.get("messages")==None:
        return jsonify({'status': 'successful notification'}), 200
    else:
        messages = value.get("messages")[0]

        phone_number = messages.get("from")
        message_type = messages.get("type")

        whatsapp_media_instance = WhatsAppGraphAPI(phone_number)
        if message_type == "text":
            message_text = messages.get("text").get("body")

        elif message_type == "image":
            image_data = messages.get("image")
            image_id = image_data.get("id")
            image_caption = image_data.get("caption")
            if image_caption==None:
                image_caption = ""
            image_path = whatsapp_media_instance.download_media(image_id, "image", image_id)
            gvapi = GoogleVisionAPI()
            message_text = image_caption + "\n\n" + gvapi.ocr_image(image_path)
        # get image and convert it into text with Google cloud vision
        # message_text = google_cloud_vision_legible_text

        elif message_type == "audio":
            audio_data = messages.get("audio")
            audio_id = audio_data.get("id")
            audio_path = whatsapp_media_instance.download_media(audio_id, "audio", audio_id)
            message_text = OpenAIAPI.transcribe_audio(audio_path)
        # Share public URL with te Whisper API
        # convert to text with the whisper API from openAI,
        # message_text = converted_audio

        tutoring_chatbot = TutoringChatbot(phone_number, message_text, message_type)
        tutoring_chatbot.process_message()

        return jsonify({'status': 'success'}), 200
