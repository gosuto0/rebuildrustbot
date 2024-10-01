初期設定
config.jsonを作成し以下の内容を記入する必要があります。
{
  "token": "DISCORDBOTTOKEN",
  "guild_id": "GUILDID",
  "channel_id": null,
  "talk_channel_id": null,
  "server_details": {
    "ip": "IPアドレス",
    "port": "PORT",
    "player_id": "プレイヤーID",
    "player_token": "PlayerToken"
  }
}
server_detailsの入力
https://chromewebstore.google.com/detail/rustpluspy-link-companion/gojhnmnggbnflhdcpcemeahejhcimnlf?hl=en
から拡張機能をダウンロードしサーバー内でペアリングを行うと以下の情報が表示されます。
{
    "desc": "",
    "id": "",
    "img": "",
    "ip": "", <- IPアドレス
    "logo": "",
    "name": "",
    "playerId": "", <- プレイヤーID
    "playerToken": "", <- プレイヤーToken
    "port": "", <- PORT
    "type": "",
    "url": ""
}
Step2 サーバー情報を送る先をDiscordにて指定する
指定したいチャンネルで /setup_channel

Step3 チームチャットを送る先をDiscordにて指定する
指定したいチャンネルで /setup_talk_channel

機能
プレイヤーの死亡とチャットをDiscordとTeamChatに送信します。
サーバー情報をDiscordとTeamChatに送信します。
