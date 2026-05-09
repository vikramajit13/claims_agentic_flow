from app.database import get_store
from app.models.policy import Policy


class PolicyRepository:
    def __init__(self) -> None:
        self.store = get_store()

    def get(self, policy_id: int) -> Policy:
        return self.store.policies[policy_id]

    def list(self) -> list[Policy]:
        return list(self.store.policies.values())
