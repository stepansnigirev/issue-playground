from rpc import BitcoinRPC
from embit.liquid.descriptor import LDescriptor
from embit.liquid.networks import get_network
import json

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

    utxos = [utxo for utxo in w.listunspent() if utxo["asset"] == LBTC]
    print(utxos)
    assert utxos

    # descriptor sanity check
    addr = DESC.derive(0).address(NETWORK)
    info = w.getaddressinfo(addr)
    assert info['ismine']

    utxo = utxos[0]
    assetinfo = w.calculateasset(utxo["txid"], utxo["vout"])
    print(assetinfo)

    rawtx = w.createrawtransaction(
        [{"txid": utxo["txid"], "vout": utxo["vout"]}],
        [{ DESC.derive(1).address(NETWORK): round(utxo["amount"]-FEE, 8)}, {"fee": FEE}]
    )
    print(rawtx)

    issueconf = {
        "asset_amount": 1000,
        "asset_address": DESC.derive(2).address(NETWORK),
        "blind": True,
        # comment out these two lines if you don't need reissuances
        "token_amount": 1,
        "token_address": DESC.derive(3).address(NETWORK),
    }

    rawissue = w.rawissueasset(rawtx, [issueconf])[0]
    if "token_amount" not in issueconf:
        del assetinfo["reissuance_asset_tag"]
    print(rawissue)

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
    with open(f"data/issue_{assetid}.json", "w") as f:
        f.write(json.dumps(obj, indent=2))

if __name__ == "__main__":
    main()