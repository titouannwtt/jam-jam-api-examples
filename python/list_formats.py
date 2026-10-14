"""Lists the input and output formats this server serves. No API key needed.

Usage: python list_formats.py [input_format]
"""
import sys

from jamjam import main, request


def run():
    input_format = sys.argv[1] if len(sys.argv) > 1 else None
    formats = request("GET", "/formats", params={"input": input_format} if input_format else None).json()

    if input_format:
        for o in formats["possibleOutputs"]:
            print(f"{o['id']:<18} " + ("allowed" if o["allowed"] else f"not allowed ({o.get('reason')})"))
        return
    print("Inputs:")
    for f in (f for f in formats["inputs"] if f["served"]):
        print(f"  {f['id']:<20} {','.join(f['extensions'])}" + ("  [account]" if f["requiresAccount"] else ""))
    print("Outputs:")
    for f in (f for f in formats["outputs"] if f["served"]):
        print(f"  {f['id']:<20} tier={f['tier']}" + ("  [account]" if f["requiresAccount"] else ""))


main(run)
