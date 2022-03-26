from embit.liquid.addresses import addr_decode, address as addr_encode
from embit.liquid.networks import get_network
from embit import ec
from embit.liquid.transaction import LTransaction, LTransactionInput, LTransactionOutput
from embit.liquid.pset import PSET
from embit.script import Script
from rpc import BitcoinRPC
import requests
import os
from pprint import pprint
from embit.util import secp256k1

API_URL = "https://blockstream.info/liquidtestnet/api"
REGTEST_ADDRESS = "el1qqt0cxdwz5cngy6luxxewglqr7v4eq5yljf7utgqz50k35kv2np0pcwn04kd6d4d9m9mjwd3xtu7q4nvq0xhau3rkf575a2ct3"
BKEY = bytes.fromhex("3e6e598aae68f2e0bf7c6e5766f27223430dcbb7bfcd56a1cec2397a072f8c6d")
NETWORK = get_network("liquidtestnet")
REGTEST = get_network("elreg")
LBTC = bytes.fromhex("144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49")[::-1]
FEE = 1000

UTXOS = [
    {"txid":"5dfb398c49bdb25ebfa87a07f0f48a926f9c3e01dd4f871c34a9d5eb31757f2c","vout":0,"status":{"confirmed":True,"block_height":273754,"block_hash":"a411ffca2d0b6649d1e51dd16c7ede97984f78db8ef425c8a5c0e2a83ce5a325","block_time":1648308372},"valuecommitment":"09cd1ce5022dc648fea74bf980883fe7cf0e4d07bd9410b1bb9702a4b4881f1369","assetcommitment":"0aa21f757c749521b92a753e7a048424a8ca55b87594c9d049e3337175cf691f2e","noncecommitment":"03ee4746d5ef1b8d1d0a9baacca6dfcb230709073ea4fab04ff388645e9fee2c1c"},
    {"txid":"14c758ed5cc63eda45202f0ccd6d3fe5a37be80b2f23ed28f67e41722abefda9","vout":1,"status":{"confirmed":True,"block_height":273749,"block_hash":"efc7d4a0207ce906737c7f35bf336dc6b0f3116b799fc9c9485c78f0815fa74c","block_time":1648308075},"valuecommitment":"09f8ab529126871a947b80b45b4feef357880d63a212d78c4ded0248b7861096b3","assetcommitment":"0a7123b8911212ac92a9cc6f6683510d342e27ff3d74fbcddfb5514eb2f0c18dbc","noncecommitment":"03de7cbddd0ee0804ecc36e3f52360b220db5c3c98a2d1897e5f678db6c33b7af3"},
    {"txid":"cc4eb2a5d8365caf3ffbf095f85d8547aa17b71f99e6b784aadb93d06c66871c","vout":0,"status":{"confirmed":True,"block_height":273757,"block_hash":"34aa5280917dc21a8d034ea2f71c4e45d0caf54184cecd7ea706e4ff16a06b87","block_time":1648308557},"valuecommitment":"0984f46e85da7f39e7480ac031e6ff279f061a43bedbb0a95d441c63b16a94ad34","assetcommitment":"0a4b4a3ef53a933309e8e4a6032df28462d85f56189276fa592d362b285603ec14","noncecommitment":"035a1e7d8f6f6d0061312e7ef5ed0d06f4666b7a258aff7f6cd9f2d859b2569658"},
]

def api_get(path, *args, **kwargs):
    url = f"{API_URL}{path}"
    print("get:", path)
    res = requests.get(url, *args, **kwargs)
    if res.status_code < 200 or res.status_code > 299:
        raise RuntimeError(res.text)
    return res

def convert_address(addr, network=NETWORK):
    sc, pub = addr_decode(addr)
    return addr_encode(sc, pub, network=network)

def main():
    addr = convert_address(REGTEST_ADDRESS)
    print(addr)
    utxos = UTXOS # api_get("/address/{addr}/utxo").json()
    txouts = []
    # searching for unspents with LBTC
    for utxo in utxos:
        txid = utxo["txid"]
        vout = utxo["vout"]
        fname = f"data/{txid}.raw"
        if not os.path.isfile(fname):
            res = api_get(f"/tx/{txid}/raw", stream=True)
            raw = res.raw.read()
            with open(fname, "wb") as f:
                f.write(raw)
        else:
            with open(fname, "rb") as f:
                raw = f.read()
        tx = LTransaction.parse(raw)
        output = tx.vout[vout]
        try:
            (value, asset, vbf, abf, *_) = output.unblind(BKEY)
        except:
            print("Failed to unblind txout")
        obj = {
            "txid": bytes.fromhex(txid),
            "vout": vout,
            "output": output,
            "value": value,
            "asset": asset,
            "vbf": vbf,
            "abf": abf,
            "asset_commitment": output.asset,
        }
        if asset == LBTC:
            txouts.append(obj)
    txouts.sort(key=lambda out: -out["value"])
    # pprint(txouts)
    # constructing transaction
    utxo = txouts[0]
    vin = [LTransactionInput(utxo["txid"], utxo["vout"])]
    sc, pub = addr_decode(addr)
    vout = [
        LTransactionOutput(LBTC, utxo["value"]-FEE, sc, pub.sec()),
        # LTransactionOutput(LBTC, 0, Script(b"\x6a"), pub.sec()),
        LTransactionOutput(LBTC, FEE, Script()),
    ]
    tx = LTransaction(vin=vin, vout=vout)
    rawtx = str(tx)

    # RPC calls
    rpc = BitcoinRPC("liquid", "secret", port=18555)
    w = rpc.wallet()
    issueconf = {
        "asset_amount": 321,
        "asset_address": convert_address("tlq1qqfsdk6xlq3xcxd5uey63r9hjse5juk0pf3ffsmlhyqxuwjz3uslzvucqcedjtlavdgttk888m69l87jkps5wvj276l02w873x", REGTEST),
        "blind": True,
        "contract_hash": "12"*32,
        "token_amount": 1,
        "token_address": convert_address("tlq1qqgy7cz7fgalxmqgg6xng2m76m862p9hz9jdjgkcveskl0uqtt2ymy82k426fqrs9vl74xdm7g6m40psjuhv4krnxw75fc9f4x", REGTEST),
    }
    rawissue = w.rawissueasset(rawtx, [issueconf])[0]
    hextx = rawissue.pop("hex")
    print(rawissue)
    asscomm = utxo["asset_commitment"].hex()
    # asscomm = secp256k1.generator_serialize(secp256k1.generator_generate(LBTC)).hex()
    print(asscomm)
    unsigned = PSET.from_string(w.converttopsbt(hextx))
    out = LTransactionOutput.parse(utxo["output"].serialize())
    out.witness=None
    unsigned.inputs[0].witness_utxo = out
    unsigned.inputs[0].range_proof = utxo["output"].witness.range_proof.serialize()
    # print(unsigned)
    blinded = w.walletprocesspsbt(str(unsigned), True)["psbt"]
    pprint(w.decodepsbt(blinded))
    # finalized = w.finalizepsbt(blinded)
    # print(finalized)
    # blinded = w.blindrawtransaction(hextx, False, [asscomm], True)
    # finalized = w.signrawtransactionwithwallet(blinded)["hex"]
    # mempooltest = w.testmempoolaccept([finalized])[0]
    # print(mempooltest)

if __name__ == '__main__':
    main()

# address/{addr}/utxo
#  "hdkeypath": "m/0'/0'/77'",
  #"hdseedid": "0432105daf6f1e18f0cca0e33e2890756e092edf",
  #"hdmasterfingerprint": "213300b9",