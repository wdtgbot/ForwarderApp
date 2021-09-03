# Telegram Forwarder App

### Functionalities

##### 1. Forward messages:

Forward messages from a chat to another chat. If you want to know how it works, go to [docs/forward.md](docs/forward.md).
To specify the source and destination you can add new rules in the _rules.json_ file. Example (note: this is just an example):

```json
{
  "forward": [
    {
      "id": "Rule 1",
      "source": -1003672971871,
      "destination": [-1001393359729, -1001452299617],
      "options": {},
      "send_copy": true,
      "remove_caption": false
    }
  ]
}
```

The structure of rules.json is very simple:

- id: Give a unique name to your rule, **make sure that is unique in this file** (Text)
- source: Source chat id, only one chat id (Number)
- destination: Destination chat ids, can be multiple (Array)
- options: Options for the message (Array)
- send_copy: Send copy or not (Boolean)
- remove_caption: Remove caption (Boolean)

For more information about the options: Go to [TDLib documentation page](https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1forward_messages.html#a6c645037c9b1fb40a3cad767f7bf2c15)

##### 2. Get main chat list:

Get main chat list of the user. Before anything, you need to know the ids of the groups that you want to add in the _rules.json_ file. This will allows you to see all information about all chats you have in the _log/output_log.json_ file. You can filter the chat you are interested in by name. If you can't find your chat, you can change in the _config.py_ file, the value of LIMIT_CHATS (be careful, if you put a larger number of chats than you have, you will get an error).

### Setup

This project depends on [TDLib](https://github.com/tdlib/td).

Basic setup:

1. Firstly, you need to get the dll/so files and put it in the lib/ folder, then you need to put the path in the \_\_lib variable. To generate these files go [here](https://tdlib.github.io/td/build.html).
2. Secondly, you need to put your API_ID and API_HASH as an environment variable in your desktop/server (recommended) or directly in the .env file. Go to [your Telegram page](https://my.telegram.org) to get them.

To execute the script:

- Run the module normally:

```
python -m forwarder
```

Once executed and authorized, the forwarder will automatically start listening to all chats specified in the rules.json file for messages to forward.

To interrupt the execution just press CTRL + C or close the CLI.

### Libraries

In the _lib/_ folder is where you should put the library files necessary to use TDLib.

### Logs

All actions and errors from the forwarder are logged in _log/app.log_.

### Issues

If you have any problems or questions, open a ticket and I will get back to you as soon as possible.
