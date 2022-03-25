from rpc import find_rpc, BitcoinRPC
import hashlib
import json
import requests

VERSION = 0
FEE = 1000e-8 # 1000 sats
ASSET_API = "https://assets-testnet.blockstream.info/"

def issue(w, ticker, name, asset_amount, domain, precision=0, token_amount=0, asset_address=None, token_address=None, pubkey=None, collection="", blind=True):
    asset_address = asset_address or w.getnewaddress()
    # TODO: pubkey should be from utxo instead
    pubkey = pubkey or w.getaddressinfo(asset_address).get("pubkey") or w.getaddressinfo(w.getnewaddress())["pubkey"]
    token_address = token_address or w.getnewaddress()
    if not collection:
        contract=f'{{"entity":{{"domain":"{domain}"}},"issuer_pubkey":"{pubkey}","name":"{name}","precision":{precision},"ticker":"{ticker}","version":{VERSION}}}'
    else:
        contract=f'{{"collection":"{collection}","entity":{{"domain":"{domain}"}},"issuer_pubkey":"{pubkey}","name":"{name}","precision":{precision},"ticker":"{ticker}","version":{VERSION}}}'
    print("Contract", contract)
    contract_hash = hashlib.sha256(contract.encode()).digest()
    print("Contract hash", contract_hash.hex())
    print("Contract hash rev", contract_hash[::-1].hex())
    # fee at least 593 sats, makes sense to set to 1000 sats to be safe

    LBTC = w.dumpassetlabels()["bitcoin"]
    # unspent LBTC outputs
    utxos = [utxo for utxo in w.listunspent(1, 9999999, [], True, {"asset": LBTC})]
    if not utxos:
        raise RuntimeError(f"Not enough funds. Send some LBTC to {w.getnewaddress()}.")

    utxos.sort(key=lambda utxo: -utxo["amount"])
    utxo = utxos[0]
    rawtx = w.createrawtransaction(
        [{"txid": utxo["txid"], "vout": utxo["vout"]}],
        [{ w.getrawchangeaddress(): round(utxo["amount"]-FEE, 8)}, {"fee": FEE}]
    )
    issueconf = {
        "asset_amount": asset_amount,
        "asset_address": asset_address,
        "blind": blind,
        "contract_hash": contract_hash[::-1].hex(),
    }
    if token_amount != 0:
        issueconf.update({
            "token_amount": token_amount,
            "token_address": token_address,
        })

    rawissue = w.rawissueasset(rawtx, [issueconf])[0]
    hextx = rawissue.pop("hex")
    print(rawissue)
    # unsigned = w.converttopsbt(rawissue["hex"])
    # blinded = w.walletprocesspsbt(unsigned)["psbt"]
    # finalized = w.finalizepsbt(blinded)['hex']
    blinded = w.blindrawtransaction(hextx, False, [], blind)
    finalized = w.signrawtransactionwithwallet(blinded)["hex"]
    mempooltest = w.testmempoolaccept([finalized])[0]
    print(mempooltest)
    if not mempooltest["allowed"]:
        raise RuntimeError(f"Tx can't be broadcasted: {mempooltest['reject-reason']}")

    contract_obj = json.loads(contract)

    assetid = rawissue["asset"]
    backup = {
        "contract": contract,
        "issueinfo": issueconf,
        "assetinfo": rawissue,
        "txinfo": mempooltest,
        # "tx": finalized,
        "registration": {
            "url": f"https://{domain}/.well_known/liquid-asset-proof-{assetid}",
            "content": f"Authorize linking the domain name {domain} to the Liquid asset {assetid}",
        },
    }
    print("Backup for asset", assetid)
    print(backup)

    # validate
    # data = {
    #     "contract": contract_obj,
    #     "contract_hash": contract_hash[::-1].hex()
    # }
    # res = requests.post(f"{ASSET_API}contract/validate", headers={'content-type': 'application/json'}, data=json.dumps(data))
    # print(res.status_code)
    # print(res.text)

def main2():
    c = '{"entity":{"domain":"embit.tech"},"issuer_pubkey":"03edc630d8e93f1de744c0cd73599e57a79f5cb8f645cce1de89e9e4e3d35406f1","name":"Burbur coin","precision":2,"ticker":"BRRCN","version":0}'
    contract_hash = hashlib.sha256(c.encode()).digest()
    print(contract_hash[::-1].hex())
    data = {
        "contract": json.loads(c),
        "contract_hash": contract_hash[::-1].hex()
    }
    data = {
        "asset_id": "ab31929af0cbbeb3c51a8060bd7ddc46d941faca073ce5a5d0d49820da1c30a5",
        "contract": json.loads(c),
    }
    print(data)
    # res = requests.post(f"{ASSET_API}contract/validate", headers={'content-type': 'application/json'}, data=json.dumps(data))
    res = requests.post(f"{ASSET_API}", headers={'content-type': 'application/json'}, data=json.dumps(data))
    print(res.status_code)
    print(res.text)

def main():
    rpc = find_rpc(net="liquidtestnet")
    a1 = "tlq1qqfsdk6xlq3xcxd5uey63r9hjse5juk0pf3ffsmlhyqxuwjz3uslzvucqcedjtlavdgttk888m69l87jkps5wvj276l02w873x"
    a2 = "tlq1qqgy7cz7fgalxmqgg6xng2m76m862p9hz9jdjgkcveskl0uqtt2ymy82k426fqrs9vl74xdm7g6m40psjuhv4krnxw75fc9f4x"
    # rpc = BitcoinRPC("liquid", "secret", port=18555)
    # a1 = "el1qqw2jxq7pln4tjlku5c7jg4jxn04le848u0s4vxhnj0ydr7jazzxz2pfl7hkxxphydjj8ngxdy9mkwg2ldy7vsrjlu8fj7h7lt"
    # a2 = "el1qqfgx87p59vv75rymang8j9nhdth2u6lhss4ekntglves2atsh3r505jeql7m659kfpadl29ndxjn9p5r9mcw5sfnzvxn37a4w"
    if True or "" not in rpc.listwallets():
        wallets = [w["name"] for w in rpc.listwalletdir()["wallets"]]
        if "" not in wallets:
            rpc.createwallet("")
    w = rpc.wallet()
    issue(w,
        ticker="EMTST",
        name="Embit test asset",
        domain="embit.tech",
        asset_amount=0.00012300,
        precision=2,
        token_amount=0.00000001,
        asset_address=a1,
        token_address=a2,
        blind=False,
    )



if __name__ == '__main__':
    main()