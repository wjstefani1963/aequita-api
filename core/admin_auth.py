"""
core/admin_auth.py

Proteção simples via HTTP Basic Auth para as rotas do admin.
As credenciais NUNCA ficam no código — vêm de variáveis de ambiente.

No Render (produção), configure em Environment:
    ADMIN_USER=seu_usuario
    ADMIN_PASS=uma_senha_forte

Localmente, coloque no seu .env:
    ADMIN_USER=wilson
    ADMIN_PASS=sua_senha_local
"""
import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def verificar_admin(credentials: HTTPBasicCredentials = Depends(security)):
    usuario_correto = os.getenv("ADMIN_USER", "")
    senha_correta = os.getenv("ADMIN_PASS", "")

    if not usuario_correto or not senha_correta:
        # Se as variáveis não estiverem configuradas, bloqueia tudo por segurança
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin não configurado: defina ADMIN_USER e ADMIN_PASS no ambiente."
        )

    # secrets.compare_digest evita "timing attack" (comparação seca de string é insegura)
    usuario_ok = secrets.compare_digest(credentials.username, usuario_correto)
    senha_ok = secrets.compare_digest(credentials.password, senha_correta)

    if not (usuario_ok and senha_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
