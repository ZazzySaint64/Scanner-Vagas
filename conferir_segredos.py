"""Confere, ANTES de publicar no GitHub, se algum segredo ou dado pessoal escapou.

Não confia só no .gitignore: abre cada arquivo que iria para o repositório e procura
  1. os VALORES reais do seu .env (senha do banco, chaves do Gemini, do agente e do n8n);
  2. formatos conhecidos de segredo (chave do Google "AIza...", token de bot do Telegram);
  3. e-mail e telefone.
Mostra só ONDE achou (arquivo e linha), nunca o valor.

Rode pelo fase6.bat (opção 3) ou: python conferir_segredos.py
"""
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
IGNORADOS = {".env", "dados", "relatorios", ".git", "__pycache__", ".venv", ".pytest_cache"}


def arquivos_publicaveis() -> list[Path]:
    """Com Git: exatamente o que o Git publicaria. Sem Git: tudo menos o que o .gitignore exclui."""
    try:
        saida = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                               cwd=RAIZ, capture_output=True, text=True, check=True).stdout
        return [RAIZ / l for l in saida.splitlines() if l]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in RAIZ.rglob("*") if p.is_file()
                and not IGNORADOS & set(p.relative_to(RAIZ).parts) and p.suffix != ".pyc"]


def segredos_do_env() -> dict[str, str]:
    env = RAIZ / ".env"
    if not env.exists():
        return {}
    valores = {}
    for linha in env.read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            nome, valor = linha.split("=", 1)
            # Só o que é segredo de verdade e tem tamanho para não dar falso alarme.
            if any(s in nome for s in ("PASSWORD", "KEY", "TOKEN", "SECRET")) and len(valor.strip()) >= 8:
                valores[nome.strip()] = valor.strip()
    return valores


PADROES = {
    "chave do Google (AIza...)": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "token de bot do Telegram": re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    "e-mail": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b"),  # "wght@400" (fonte) não casa
    "telefone": re.compile(r"\(?\b\d{2}\)?\s?9\d{4}-?\d{4}\b"),
}
# E-mails que aparecem de propósito no código (exemplos e casos de ataque).
EMAILS_OK = {"noreply@anthropic.com", "rh@empresa.com", "talentos@exemplo-rh.com", "rh@exemplo.com"}


def main() -> int:
    env = segredos_do_env()
    achados = []
    arquivos = arquivos_publicaveis()
    for arq in arquivos:
        try:
            linhas = arq.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue  # binário
        rel = arq.relative_to(RAIZ)
        for n, linha in enumerate(linhas, 1):
            for nome, valor in env.items():
                if valor in linha:
                    achados.append(f"{rel}:{n}  valor de {nome} do .env")
            for nome, rx in PADROES.items():
                for m in rx.findall(linha):
                    if nome == "e-mail" and (m in EMAILS_OK or "noreply" in m
                                             or m.endswith(("example.com", "exemplo.com"))):
                        continue
                    achados.append(f"{rel}:{n}  {nome}")
    print(f"Arquivos conferidos: {len(arquivos)} (o .env, dados/ e relatorios/ ficam de fora)")
    print(f"Segredos do .env procurados: {', '.join(env) or 'nenhum (.env não encontrado)'}")
    if achados:
        print("\nATENÇÃO, encontrado (corrija antes de publicar):")
        print("\n".join(f"  {a}" for a in achados))
        return 1
    print("\nNada encontrado. Pode publicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
