"""
Gerenciamento de jobs em background (importação, geração de informes).
Jobs ficam em memória — suficiente para uso local em produção.
"""
import uuid
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

_jobs: dict[str, "Job"] = {}
_lock = threading.Lock()

# Impede que dois jobs do mesmo tipo rodem ao mesmo tempo
_running: dict[str, bool] = {}


@dataclass
class Job:
    id: str
    tipo: str
    status: str = "running"      # running | ok | erro
    iniciado_em: datetime = field(default_factory=datetime.now)
    finalizado_em: Optional[datetime] = None
    mensagem: str = ""
    resultado: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "status": self.status,
            "iniciado_em": self.iniciado_em.isoformat(),
            "finalizado_em": self.finalizado_em.isoformat() if self.finalizado_em else None,
            "mensagem": self.mensagem,
            "resultado": self.resultado,
        }


def is_running(tipo: str) -> bool:
    return _running.get(tipo, False)


def criar_job(tipo: str) -> Job:
    job = Job(id=str(uuid.uuid4()), tipo=tipo)
    with _lock:
        _jobs[job.id] = job
        _running[tipo] = True
    return job


def finalizar_job(job: Job, status: str, mensagem: str, resultado: dict = None):
    with _lock:
        job.status = status
        job.mensagem = mensagem
        job.finalizado_em = datetime.now()
        job.resultado = resultado or {}
        _running[job.tipo] = False


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def listar_jobs(limit: int = 30) -> list[Job]:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j.iniciado_em, reverse=True)[:limit]
