from gen_issue import *
import json
import os
from embit.liquid.pset import PSET
from embit.liquid.transaction import LTransaction
from embit import ec, bip39, bip32
from embit.script import p2pkh_from_p2wpkh
import sys

def main():
    root = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(MNEMONIC))
    files = [f for f in os.listdir("data") if f.endswith(".json")]
    for file in files:
        fname = os.path.join("data", file)
        with open(fname, "r") as f:
            obj = json.load(f)
        # already signed
        if "sighash_rangeproof" in obj["issue"]:
            continue
        b64psbt = obj["issue"]["blinded"]
        pset = PSET.from_string(b64psbt)
        inp = pset.inputs[0]

        print(pset.inputs[0].vout)
        tx = LTransaction.from_string(obj["issue"]["finalized"])
        vin = tx.vin[0]
        iss = vin.asset_issuance
        # print(iss.nonce)
        # print(iss.entropy)
        # print(iss.amount_commitment)
        # print(iss.token_commitment)
        sighash = (tx.sighash_segwit(0, p2pkh_from_p2wpkh(inp.utxo.script_pubkey), inp.utxo.value, 1))
        print(sighash)
        sig, pub = vin.witness.script_witness.items
        sig = ec.Signature.parse(sig[:-1])
        pub = ec.PublicKey.parse(pub)
        print(pub.verify(sig, sighash)) # Yey! True!

        btx = pset.blinded_tx
        sighash = (btx.sighash_segwit(0, p2pkh_from_p2wpkh(inp.utxo.script_pubkey), inp.utxo.value, 1))
        print(sighash)

        pset.sign_with(root, 0x41)
        obj["issue"]["sighash_rangeproof"] = str(pset)
        with open(fname, "w") as f:
            f.write(json.dumps(obj, indent=2))

# b'\xfc\x04pset\x00' - issue amount (little endian)
# b'\xfc\x04pset\x01' - issue value commitment
# b'\xfc\x04pset\x02' - issue value rangeproof
# b'\xfc\x04pset\x03' - reissue value rangeproof
# b'\xfc\x04pset\x0a' - reissuance token amount (little endian)
# b'\xfc\x04pset\x0b' - reissue value commitment
# b'\xfc\x04pset\x0f' - issue value proof
# b'\xfc\x04pset\x10' - reissue value proof

if __name__ == "__main__":
    main()