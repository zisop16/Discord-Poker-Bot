from DataManager import *

class CommandInterface:
    def __init__(self, data_manager, prefix='-'):
        self.data_manager = data_manager
        self.prefix = prefix

    """
    def parse_command(self, message):
        text = message.content
        userID = message.author.id
        if text.startswith(self.prefix):
            text = text[1:]
            info = text.split(' ')
            command = info[0]
            arguments = info[1:]
            channel = message.channel
        else: 
            return False
        valid_command = False
        match(command):
            case "enable":
                self.enable_channel(channel)
                valid_command = True
            case "disable":
                self.disable_channel(channel)
                valid_command = True

        return valid_command
    """

    def enable_channel(self, channel):
        id = channel.id
        self.data_manager.enable_channel(id)

    def disable_channel(self, channel):
        id = channel.id
        self.data_manager.disable_channel(id)

    def generate_chips(self, userID):
        received, remaining_time = self.data_manager.generate_chips(userID)
        if received:
            pass


    def create_table(self, userID, arguments):
        pass


if __name__ == '__main__':
    command = "-paycheck"
    load_dotenv(find_dotenv())
    password = os.getenv("MONGO_PASS")
    manager = DataManager(password)