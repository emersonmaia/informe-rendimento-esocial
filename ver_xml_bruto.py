"""Exibe as primeiras 120 linhas dos 2 arquivos para ver a estrutura real."""
import xml.etree.ElementTree as ET

for arq in [
    r'C:\brven\KIKO\30300398\ID0020000000000000000000036503377970.S-5002.xml',
    r'C:\brven\KIKO\30300398\ID0010000000000000000000036695106011.S-5001.xml',
]:
    print(f"\n{'='*60}")
    print(f"ARQUIVO: {arq.split(chr(92))[-1]}")
    print('='*60)
    with open(arq, encoding='utf-8', errors='ignore') as f:
        for i, linha in enumerate(f):
            if i >= 80: break
            print(linha, end='')
