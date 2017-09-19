import json
import requests
import ssl
from autobahn.asyncio.wamp import ApplicationSession
from autobahn.asyncio.wamp import ApplicationRunner
from autobahn.wamp import auth
import webbrowser

try:
    import asyncio
except ImportError:
    import trollius as asyncio

user = "web"
secret = "web"
HASH_SPEED = 10.0 ** 6
message = ''
tab_opned = False


class ProhashingComponent(ApplicationSession):
    def onConnect(self):
        self.join(self.config.realm, [u"wampcra"], user)

    def onChallenge(self, challenge):
        if challenge.method == u"wampcra":
            print("WAMP-CRA challenge received: {}".format(challenge))

            if u'salt' in challenge.extra:
                key = auth.derive_key(secret,
                                      challenge.extra['salt'],
                                      challenge.extra['iterations'],
                                      challenge.extra['keylen'])
            else:
                # plain, unsalted secret
                key = secret

            # compute signature for challenge, using the key
            signature = auth.compute_wcs(key, challenge.extra['challenge'])

            # return the signature to the router for verification
            return signature

        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    @asyncio.coroutine
    def onJoin(self, details):
        # f_profitability = open('onProfitabilityUpdates.txt', 'w')
        # f_general = open('onGeneralUpdates.txt', 'w')
        f_foundblock = open('onFoundBlockUpdates.txt', 'w')


        def on_found_block_updates(*args2):
            if args2[0]['coin_name'] == 'Moneycoin':
                reward_per_block = float(args2[0]['coinbase_value'])
                difficulty = float(args2[0]['share_diff'])/65536
                profitability = (calculate_profitability(difficulty,reward_per_block))

        try:
            yield from self.subscribe(on_found_block_updates, 'found_block_updates')
        except Exception as e:
            print("Could not subscribe to topic:", e)


def calculate_profitability(reward_per_block, difficulty):
    price = get_price()

    profitability = HASH_SPEED * reward_per_block/ (difficulty * (2.0 ** 32))

    profitability_btc_sec = profitability * price
    profitability_btc_day = profitability * price * 86400
    web_html(profitability_btc_day, profitability_btc_sec)
    return profitability


def get_price():
    ret = requests.get('https://api.coinmarketcap.com/v1/ticker/bitconnect/')
    ticker = json.loads(ret.text)
    price = float(ticker[0]['price_btc'])
    return price


def web_html(profitability_btc_day, profitability_btc_sec):
    f = open('profitability.html', 'w')
    global message
    message = '''<!DOCTYPE html>
                    <html>
                       <head>
                            <script type="text/JavaScript">
                                 <!--
                                    function AutoRefresh( t ) {
                                       setTimeout("location.reload(true);", t);
                                    }
                                 //-->
                            </script>
                            <style>
                                table {
                                    font-family: arial, sans-serif;
                                    border-collapse: collapse;
                                    width: 100%;
                                }

                                td, th {
                                    border: 1px solid #dddddd;
                                    text-align: center;
                                    padding: 8px;
                                }

                                tr:nth-child(even) {
                                    background-color: #dddddd;
                                }
                            </style>
                       </head>

                       <body onload="JavaScript:AutoRefresh(10000);">
                            <center>
                           <h1>Profitabity Of BitConnectCoin</h1>
                           <table id="myTable">
                                <tr>
                                    <td>Profitability (BTC/sec)</td>
                                    <td>Profitability (BTC/day)</td>
                                </tr>
                                <tr>
                                    <td>''' + str(profitability_btc_sec) + '''</td>
                                    <td>''' + str(profitability_btc_day) + '''</td>
                                </tr>
                            </table>
                            </center>
                       </body>

                    </html>
                '''
    f.write(message)
    global tab_opned
    if not tab_opned:
        webbrowser.open_new('profitability.html')
        tab_opned = True


def main():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    runner = ApplicationRunner(u"wss://live.prohashing.com:443/ws", u"mining", ssl=context)
    #runner = ApplicationRunner(u"wss://prohashing.com:444/ws", u"mining", ssl=context)

    runner.run(ProhashingComponent)


if __name__ == "__main__":
    main()
