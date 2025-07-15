import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QLabel, QTextEdit, QListWidget, 
                              QPushButton, QLineEdit, QListWidgetItem)  # Added QListWidgetItem here
from PySide6.QtCore import Qt, QThread, Signal
import telebot
from telebot.types import Message

class TelegramBotWorker(QThread):
    new_message = Signal(dict)  # Signal to emit when new message arrives
    
    def __init__(self, api_token):
        super().__init__()
        self.bot = telebot.TeleBot(api_token)
        self.running = True
        
        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message):
            self.new_message.emit({
                'chat_id': message.chat.id,
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'text': message.text
            })
    
    def run(self):
        while self.running:
            try:
                self.bot.polling(none_stop=True, interval=1)
            except Exception as e:
                print(f"Polling error: {e}")
    
    def stop(self):
        self.running = False
        self.bot.stop_polling()

class TelegramBotUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Customer Reply Bot")
        self.setGeometry(100, 100, 800, 600)
        
        # Bot state
        self.bot_worker = None
        self.current_chat_id = None
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - chat list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # API Token input
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter Telegram Bot API Token")
        left_layout.addWidget(QLabel("Bot API Token:"))
        left_layout.addWidget(self.token_input)
        
        # Start/Stop button
        self.control_button = QPushButton("Start Bot")
        self.control_button.clicked.connect(self.toggle_bot)
        left_layout.addWidget(self.control_button)
        
        # Chat list
        left_layout.addWidget(QLabel("Active Chats:"))
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.select_chat)
        left_layout.addWidget(self.chat_list)
        
        # Right panel - chat area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Chat info
        self.chat_info = QLabel("Select a chat to view messages")
        right_layout.addWidget(self.chat_info)
        
        # Message display
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        right_layout.addWidget(self.message_display)
        
        # Reply area
        self.reply_input = QTextEdit()
        self.reply_input.setPlaceholderText("Type your reply here...")
        right_layout.addWidget(self.reply_input)
        
        # Send button
        self.send_button = QPushButton("Send Reply")
        self.send_button.clicked.connect(self.send_reply)
        right_layout.addWidget(self.send_button)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
    def toggle_bot(self):
        if self.bot_worker and self.bot_worker.isRunning():
            # Stop the bot
            self.bot_worker.stop()
            self.bot_worker.quit()
            self.bot_worker.wait()
            self.control_button.setText("Start Bot")
            self.token_input.setEnabled(True)
            self.statusBar().showMessage("Bot stopped", 3000)
        else:
            # Start the bot
            token = self.token_input.text().strip()
            if not token:
                self.statusBar().showMessage("Please enter a valid API token", 3000)
                return
                
            self.bot_worker = TelegramBotWorker(token)
            self.bot_worker.new_message.connect(self.handle_new_message)
            self.bot_worker.start()
            self.control_button.setText("Stop Bot")
            self.token_input.setEnabled(False)
            self.statusBar().showMessage("Bot started", 3000)
    
    def handle_new_message(self, message_data):
        chat_id = message_data['chat_id']
        username = message_data['username'] or "No username"
        first_name = message_data['first_name'] or "Unknown"
        text = message_data['text']
        
        # Find or create chat in list
        chat_item = None
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if int(item.data(Qt.UserRole)) == chat_id:
                chat_item = item
                break
                
        if not chat_item:
            chat_item = QListWidgetItem(f"{first_name} (@{username})")
            chat_item.setData(Qt.UserRole, chat_id)
            self.chat_list.addItem(chat_item)
        
        # If this is the currently selected chat, update the display
        if self.current_chat_id == chat_id:
            self.append_message(f"{first_name}: {text}")
    
    def select_chat(self, item):
        self.current_chat_id = item.data(Qt.UserRole)
        username = item.text().split("@")[-1].rstrip(")")
        first_name = item.text().split(" ")[0]
        self.chat_info.setText(f"Chat with {first_name} (@{username})")
        self.message_display.clear()
        self.message_display.append("Loading chat history...")
        # Here you would load previous messages from the bot's memory or database
    
    def append_message(self, text):
        self.message_display.append(text)
        self.message_display.verticalScrollBar().setValue(
            self.message_display.verticalScrollBar().maximum()
        )
    
    def send_reply(self):
        if not self.current_chat_id:
            self.statusBar().showMessage("No chat selected", 3000)
            return
            
        if not self.bot_worker or not self.bot_worker.isRunning():
            self.statusBar().showMessage("Bot is not running", 3000)
            return
            
        reply_text = self.reply_input.toPlainText().strip()
        if not reply_text:
            self.statusBar().showMessage("Reply text is empty", 3000)
            return
            
        try:
            # Send the message
            self.bot_worker.bot.send_message(self.current_chat_id, reply_text)
            self.append_message(f"You: {reply_text}")
            self.reply_input.clear()
            self.statusBar().showMessage("Message sent", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error sending message: {str(e)}", 5000)
    
    def closeEvent(self, event):
        if self.bot_worker and self.bot_worker.isRunning():
            self.bot_worker.stop()
            self.bot_worker.quit()
            self.bot_worker.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TelegramBotUI()
    window.show()
    sys.exit(app.exec())