class Lobby:
    # self.owner: Discord.User
    # self._id: string, NYI
    # self.joined: Discord.User[]
    def __init__(self, owner, _id=None):
        self.owner = owner
        self._id = _id or Lobby.generate_id()

        # Initialize the list of players who have joined this lobby
        self.joined = [owner]

    def __str__(self):
        # Check edge case, 0 players
        if len(self.joined) is 0:
            print('Could not convert lobby object to string representation, zero items in self.joined')
            return ''

        # Check edge case, 1 player
        if len(self.joined) is 1:
            return str(self.joined[0].name)

        # Check edge case, 2 players
        if len(self.joined) is 2:
            return ' and '.join(user.name for user in self.joined)

        # Format a comma-separated list of users' names currently in the lobby.
        # First begin with all but the last user.
        output = ', '.join(user.name for user in self.joined[:-1])

        # Then add our last user with a nicely formatted 'and'
        output += f', and {self.joined[-1].name}'

        return output

    def add_user(self, user):
        self.joined.append(user)

    def remove_user(self, user):
        if user in self.joined:
            self.joined.remove(user)

            if self.is_owner(user):
                if self.user_count() is not 0:
                    self.owner = self.joined[0]
                else:
                    print('No new owner could be assigned because there are no other players readied up.');

    def contains_user(self, user):
        return user in self.joined

    def user_count(self):
        return len(self.joined)

    def is_owner(self, user):
        return self.owner == user

    def get_owner(self):
        return self.owner

    def get_users(self):
        return self.joined

    @staticmethod
    def generate_id():
        return '1234' # Placeholder