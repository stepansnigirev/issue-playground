from rpc import BitcoinRPC
from embit.liquid.descriptor import LDescriptor
from embit.liquid.networks import get_network
import json
import os

from pprint import pprint

MNEMONIC = "pencil crack couch kick pattern next lyrics clarify video element advance corn"
DESC = LDescriptor.from_string("blinded(slip77(L27UZV4obh7NRD4cJudb3P8mpDwFzDC8Uipv2Kj6JtjiM5uAiu4y),wpkh([2a6f2c67/84h/1h/0h]tpubDDA19zi2TR2GEVudztjs147oZbdLZqaNTLAe8Pm5FF8Gi7GHg6kFAoFZuqnQZvur5WycrtSSnJGAf2koQcv8HJ77pZgVjn9HSzAyDSaS3m4/{0,1}/*))")
NETWORK = get_network('embit')
FEE = 1500e-8

def main():
    rpc = BitcoinRPC("liquid", "secret", port=18555)
    print(rpc.getmininginfo())

    LBTC = rpc.dumpassetlabels()["bitcoin"]

    # default wallet
    w = rpc.wallet("specter/pencil")
    wh = rpc.wallet("specter_hotstorage/pencil")
    print(w.getbalances())

    unspent = w.listunspent()
    utxos = [utxo for utxo in unspent if utxo["asset"] == LBTC]
    print(utxos)
    assert utxos
    btc_utxo = utxos[0]

    # descriptor sanity check
    addr = DESC.derive(0).address(NETWORK)
    info = w.getaddressinfo(addr)
    assert info['ismine']

    files = [f for f in os.listdir("data") if f.endswith(".json") and f.startswith("issue_")]
    for fname in files:
        with open(os.path.join("data", fname), "r") as f:
            obj = json.load(f)
        reissue_asset = obj["issue"]["assetinfo"].get("reissuance_asset_tag")
        if not reissue_asset:
            print(f"{fname} skipped - no reissue asset")
            continue
        print(reissue_asset)
        utxos = [utxo for utxo in unspent if utxo["asset"] == reissue_asset]
        if not utxos:
            print(f"{fname} skipped - no reissue balance")
        utxo = utxos[0]
        assetinfo = obj["issue"]["assetinfo"]
        issueinfo = obj["issue"]["rawissue"]
        print(utxo)

        rawtx = w.createrawtransaction([
                {"txid": utxo["txid"], "vout": utxo["vout"]},
                {"txid": btc_utxo["txid"], "vout": btc_utxo["vout"]},
            ],
            [
                { DESC.derive(1).address(NETWORK): utxo["amount"], "asset": reissue_asset},
                { DESC.derive(2).address(NETWORK): round(btc_utxo["amount"]-FEE, 8)},
                {"fee": FEE},
            ]
        )
        print(rawtx)

        print(issueinfo)
        rawissue = w.rawreissueasset(rawtx, [{
            "asset_amount": 200,
            "asset_address": DESC.derive(2).address(NETWORK),
            "input_index": 0,
            "entropy": issueinfo["entropy"],
            "asset_blinder": utxo["assetblinder"],
        }])

        unsigned = w.converttopsbt(rawissue["hex"])
        print(unsigned)

        blinded = w.walletprocesspsbt(unsigned)['psbt']

        signed = wh.walletprocesspsbt(blinded)['psbt']

        finalized = w.finalizepsbt(signed)['hex']
        mempooltest = w.testmempoolaccept([finalized])
        print(mempooltest)

        obj = {
            "wallet": {
                "mnemonic": MNEMONIC,
                "descriptor": str(DESC),
            },
            "issue": {
                "utxo": utxo,
                "assetinfo": assetinfo,
                "rawtx": rawtx,
                "rawissue": rawissue,
                "unsigned": unsigned,
                "blinded": blinded,
                "signed": signed,
                "finalized": finalized,
                "mempooltest": mempooltest,
            }
        }
        assetid = assetinfo["asset_tag"]
        with open(f"data/reissue_{assetid}.json", "w") as f:
            f.write(json.dumps(obj, indent=2))

if __name__ == "__main__":
    main()