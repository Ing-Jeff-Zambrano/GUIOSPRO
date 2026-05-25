"""Inicializa almacenamiento local o PostgreSQL (tablas + datos demo)."""

from __future__ import annotations

from auth.service import hash_password
from db.config import storage_label
from db.models import Organizacion, Usuario
from db.session import get_session, init_tables
from services.catalog import seed_catalog_if_empty
from sqlalchemy import select

_bootstrapped = False


def seed_users() -> None:
    with get_session() as session:
        org = session.execute(
            select(Organizacion).where(Organizacion.nombre == "Empresa Demo S.A.")
        ).scalar_one_or_none()
        if not org:
            org = Organizacion(nombre="Empresa Demo S.A.")
            session.add(org)
            session.flush()

        users = [
            ("decisor", "Decisor2025!", "decisor", "Jefferson Zambrano"),
            ("consultor", "Consultor2025!", "consultor", "Luis Pérez — Consultor"),
            ("admin", "Admin2025!", "admin", "Admin Sistema"),
        ]
        for username, password, rol, nombre in users:
            exists = session.execute(
                select(Usuario).where(Usuario.username == username)
            ).scalar_one_or_none()
            if exists:
                exists.nombre_completo = nombre
                continue
            session.add(
                Usuario(
                    organizacion_id=org.id,
                    username=username,
                    email=f"{username}@demo.guiospro.local",
                    password_hash=hash_password(password),
                    rol=rol,
                    nombre_completo=nombre,
                )
            )
        session.commit()


def ensure_database_ready() -> str:
    """
    Crea tablas y datos iniciales si hace falta.
    Devuelve etiqueta del modo de almacenamiento.
    """
    global _bootstrapped
    if _bootstrapped:
        return storage_label()

    init_tables()
    seed_catalog_if_empty()
    seed_users()
    _bootstrapped = True
    return storage_label()
