"""Project-specific entry points; inference credentials come from the environment."""
import argparse, json, uuid
from pathlib import Path
from .common import ROOT
def output(v): print(json.dumps(v,ensure_ascii=False,indent=2))
def main():
    p=argparse.ArgumentParser(prog='quality-gate')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('results',help='Read the measured summary without API calls')
    e=sub.add_parser('evaluate');e.add_argument('--out',type=Path,required=True)
    v=sub.add_parser('verify');v.add_argument('--domain',choices=['artifact','business'],required=True);v.add_argument('--candidate',type=Path,required=True);v.add_argument('--oracle',type=Path,required=True)
    a=p.parse_args()
    if a.command=='results':
        output(json.loads((ROOT/'results/measured_summary.json').read_text()));return
    from .quality import evaluate_lab, verify
    if a.command=='evaluate':output(evaluate_lab(a.out));return
    output(verify(a.domain,json.loads(a.candidate.read_text()),json.loads(a.oracle.read_text())))
if __name__=='__main__':main()
