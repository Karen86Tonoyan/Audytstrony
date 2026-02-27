#!/usr/bin/env python3
"""
OpenFGA Adapter for ALFA Security Layer

Integrates OpenFGA (Fine-Grained Authorization) with ALFA for:
- Relationship-based access control (ReBAC)
- Fine-grained permissions per agent/worker
- Dynamic permission evaluation

OpenFGA Model for SWARM:
    type user
    type agent
        relations
            define owner: [user]
            define operator: [user]
            define viewer: [user] or operator or owner

    type swarm
        relations
            define admin: [user, agent]
            define controller: [user, agent] or admin
            define worker: [agent]
            define can_start: controller
            define can_stop: admin
            define can_scale: controller
            define can_view: viewer

    type cerber
        relations
            define admin: [user]
            define can_configure: admin
            define can_trigger_chaos: admin
"""

import asyncio
import httpx
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# OpenFGA Model for SWARM system
SWARM_AUTHORIZATION_MODEL = {
    "schema_version": "1.1",
    "type_definitions": [
        {
            "type": "user",
            "relations": {},
            "metadata": None
        },
        {
            "type": "agent",
            "relations": {
                "owner": {
                    "this": {}
                },
                "operator": {
                    "this": {}
                },
                "viewer": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "operator"}},
                            {"computedUserset": {"relation": "owner"}}
                        ]
                    }
                }
            },
            "metadata": {
                "relations": {
                    "owner": {"directly_related_user_types": [{"type": "user"}]},
                    "operator": {"directly_related_user_types": [{"type": "user"}]},
                    "viewer": {"directly_related_user_types": [{"type": "user"}]}
                }
            }
        },
        {
            "type": "swarm",
            "relations": {
                "admin": {
                    "this": {}
                },
                "controller": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "admin"}}
                        ]
                    }
                },
                "worker": {
                    "this": {}
                },
                "can_start": {
                    "computedUserset": {"relation": "controller"}
                },
                "can_stop": {
                    "computedUserset": {"relation": "admin"}
                },
                "can_scale": {
                    "computedUserset": {"relation": "controller"}
                },
                "can_view": {
                    "computedUserset": {"relation": "controller"}
                }
            },
            "metadata": {
                "relations": {
                    "admin": {"directly_related_user_types": [
                        {"type": "user"},
                        {"type": "agent"}
                    ]},
                    "controller": {"directly_related_user_types": [
                        {"type": "user"},
                        {"type": "agent"}
                    ]},
                    "worker": {"directly_related_user_types": [{"type": "agent"}]}
                }
            }
        },
        {
            "type": "cerber",
            "relations": {
                "admin": {
                    "this": {}
                },
                "can_configure": {
                    "computedUserset": {"relation": "admin"}
                },
                "can_trigger_chaos": {
                    "computedUserset": {"relation": "admin"}
                }
            },
            "metadata": {
                "relations": {
                    "admin": {"directly_related_user_types": [{"type": "user"}]}
                }
            }
        },
        {
            "type": "memory",
            "relations": {
                "owner": {
                    "this": {}
                },
                "can_read": {
                    "computedUserset": {"relation": "owner"}
                },
                "can_write": {
                    "computedUserset": {"relation": "owner"}
                }
            },
            "metadata": {
                "relations": {
                    "owner": {"directly_related_user_types": [
                        {"type": "agent"},
                        {"type": "swarm"}
                    ]}
                }
            }
        }
    ]
}


class Permission(Enum):
    """Permissions for SWARM operations."""
    # Swarm permissions
    SWARM_START = ("swarm", "can_start")
    SWARM_STOP = ("swarm", "can_stop")
    SWARM_SCALE = ("swarm", "can_scale")
    SWARM_VIEW = ("swarm", "can_view")

    # Cerber permissions
    CERBER_CONFIGURE = ("cerber", "can_configure")
    CERBER_CHAOS = ("cerber", "can_trigger_chaos")

    # Memory permissions
    MEMORY_READ = ("memory", "can_read")
    MEMORY_WRITE = ("memory", "can_write")


@dataclass
class AuthorizationResult:
    """Result of an authorization check."""
    allowed: bool
    reason: str
    resolution_time_ms: float = 0.0


class OpenFGAClient:
    """
    Client for OpenFGA server.

    Handles:
    - Store creation/management
    - Authorization model setup
    - Relationship tuples (who has what relation to what)
    - Authorization checks
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        store_id: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.store_id = store_id
        self.authorization_model_id: Optional[str] = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def initialize(self) -> bool:
        """Initialize OpenFGA store and model."""
        try:
            # Check if server is available
            response = await self._client.get(f"{self.base_url}/healthz")
            if response.status_code != 200:
                logger.warning("OpenFGA server not available")
                return False

            # Create or get store
            if not self.store_id:
                self.store_id = await self._create_store("swarm-auth")

            # Write authorization model
            self.authorization_model_id = await self._write_authorization_model()

            logger.info(f"OpenFGA initialized: store={self.store_id}, model={self.authorization_model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize OpenFGA: {e}")
            return False

    async def _create_store(self, name: str) -> str:
        """Create a new OpenFGA store."""
        response = await self._client.post(
            f"{self.base_url}/stores",
            json={"name": name}
        )
        response.raise_for_status()
        return response.json()["id"]

    async def _write_authorization_model(self) -> str:
        """Write the SWARM authorization model."""
        response = await self._client.post(
            f"{self.base_url}/stores/{self.store_id}/authorization-models",
            json=SWARM_AUTHORIZATION_MODEL
        )
        response.raise_for_status()
        return response.json()["authorization_model_id"]

    async def write_tuple(
        self,
        user: str,
        relation: str,
        object_type: str,
        object_id: str,
    ) -> bool:
        """
        Write a relationship tuple.

        Example: write_tuple("user:alice", "admin", "swarm", "main")
        Creates: user:alice is admin of swarm:main
        """
        response = await self._client.post(
            f"{self.base_url}/stores/{self.store_id}/write",
            json={
                "writes": {
                    "tuple_keys": [{
                        "user": user,
                        "relation": relation,
                        "object": f"{object_type}:{object_id}"
                    }]
                },
                "authorization_model_id": self.authorization_model_id
            }
        )
        return response.status_code == 200

    async def delete_tuple(
        self,
        user: str,
        relation: str,
        object_type: str,
        object_id: str,
    ) -> bool:
        """Delete a relationship tuple."""
        response = await self._client.post(
            f"{self.base_url}/stores/{self.store_id}/write",
            json={
                "deletes": {
                    "tuple_keys": [{
                        "user": user,
                        "relation": relation,
                        "object": f"{object_type}:{object_id}"
                    }]
                },
                "authorization_model_id": self.authorization_model_id
            }
        )
        return response.status_code == 200

    async def check(
        self,
        user: str,
        relation: str,
        object_type: str,
        object_id: str,
    ) -> AuthorizationResult:
        """
        Check if user has relation to object.

        Example: check("user:alice", "can_start", "swarm", "main")
        Returns: AuthorizationResult(allowed=True/False, ...)
        """
        import time
        start = time.perf_counter()

        try:
            response = await self._client.post(
                f"{self.base_url}/stores/{self.store_id}/check",
                json={
                    "tuple_key": {
                        "user": user,
                        "relation": relation,
                        "object": f"{object_type}:{object_id}"
                    },
                    "authorization_model_id": self.authorization_model_id
                }
            )

            elapsed_ms = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                return AuthorizationResult(
                    allowed=data.get("allowed", False),
                    reason="OpenFGA check passed" if data.get("allowed") else "OpenFGA check denied",
                    resolution_time_ms=elapsed_ms
                )
            else:
                return AuthorizationResult(
                    allowed=False,
                    reason=f"OpenFGA error: {response.status_code}",
                    resolution_time_ms=elapsed_ms
                )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return AuthorizationResult(
                allowed=False,
                reason=f"OpenFGA exception: {e}",
                resolution_time_ms=elapsed_ms
            )

    async def list_objects(
        self,
        user: str,
        relation: str,
        object_type: str,
    ) -> List[str]:
        """
        List all objects of type that user has relation to.

        Example: list_objects("user:alice", "can_view", "swarm")
        Returns: ["swarm:main", "swarm:test"]
        """
        response = await self._client.post(
            f"{self.base_url}/stores/{self.store_id}/list-objects",
            json={
                "user": user,
                "relation": relation,
                "type": object_type,
                "authorization_model_id": self.authorization_model_id
            }
        )

        if response.status_code == 200:
            return response.json().get("objects", [])
        return []

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


class OpenFGAAuthAdapter:
    """
    Adapter that integrates OpenFGA with ALFA's AuthManager.

    Provides:
    - Fine-grained permission checks
    - Relationship-based access control
    - Falls back to JWT roles when OpenFGA unavailable
    """

    def __init__(
        self,
        openfga_url: str = "http://localhost:8080",
        fallback_to_jwt: bool = True,
    ):
        self.client = OpenFGAClient(base_url=openfga_url)
        self.fallback_to_jwt = fallback_to_jwt
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize OpenFGA connection."""
        self._initialized = await self.client.initialize()
        return self._initialized

    async def setup_default_permissions(
        self,
        admin_user: str = "user:hermes",
    ):
        """Setup default permission structure."""
        if not self._initialized:
            return

        # Hermes agent is admin of main swarm
        await self.client.write_tuple(admin_user, "admin", "swarm", "main")

        # Hermes is admin of Cerber
        await self.client.write_tuple(admin_user, "admin", "cerber", "main")

        # Swarm owns shared memory
        await self.client.write_tuple("swarm:main", "owner", "memory", "shared")

        logger.info("Default OpenFGA permissions configured")

    async def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_id: str = "main",
        jwt_role: Optional[str] = None,
    ) -> AuthorizationResult:
        """
        Check if user has permission on resource.

        Falls back to JWT role-based check if OpenFGA unavailable.
        """
        object_type, relation = permission.value

        if self._initialized:
            # Use OpenFGA for fine-grained check
            return await self.client.check(
                user=f"user:{user_id}",
                relation=relation,
                object_type=object_type,
                object_id=resource_id,
            )

        elif self.fallback_to_jwt and jwt_role:
            # Fallback to simple role-based check
            return self._jwt_role_check(jwt_role, permission)

        else:
            return AuthorizationResult(
                allowed=False,
                reason="Authorization system unavailable"
            )

    def _jwt_role_check(self, role: str, permission: Permission) -> AuthorizationResult:
        """Simple role-based permission check (fallback)."""
        role_permissions = {
            "admin": [
                Permission.SWARM_START, Permission.SWARM_STOP,
                Permission.SWARM_SCALE, Permission.SWARM_VIEW,
                Permission.CERBER_CONFIGURE, Permission.CERBER_CHAOS,
                Permission.MEMORY_READ, Permission.MEMORY_WRITE,
            ],
            "operator": [
                Permission.SWARM_START, Permission.SWARM_SCALE,
                Permission.SWARM_VIEW, Permission.MEMORY_READ,
            ],
            "viewer": [
                Permission.SWARM_VIEW, Permission.MEMORY_READ,
            ],
        }

        allowed_permissions = role_permissions.get(role, [])
        allowed = permission in allowed_permissions

        return AuthorizationResult(
            allowed=allowed,
            reason=f"JWT role '{role}' {'has' if allowed else 'lacks'} {permission.name}"
        )

    async def grant_permission(
        self,
        user_id: str,
        relation: str,
        object_type: str,
        object_id: str,
    ) -> bool:
        """Grant a permission (write tuple)."""
        if not self._initialized:
            return False
        return await self.client.write_tuple(
            f"user:{user_id}", relation, object_type, object_id
        )

    async def revoke_permission(
        self,
        user_id: str,
        relation: str,
        object_type: str,
        object_id: str,
    ) -> bool:
        """Revoke a permission (delete tuple)."""
        if not self._initialized:
            return False
        return await self.client.delete_tuple(
            f"user:{user_id}", relation, object_type, object_id
        )

    async def list_user_permissions(
        self,
        user_id: str,
        object_type: str,
    ) -> List[str]:
        """List all objects of type that user can access."""
        if not self._initialized:
            return []

        # Check common relations
        results = []
        for relation in ["admin", "controller", "can_view", "owner"]:
            objects = await self.client.list_objects(
                f"user:{user_id}", relation, object_type
            )
            results.extend(objects)

        return list(set(results))  # Remove duplicates

    async def close(self):
        """Cleanup resources."""
        await self.client.close()


# Integration with ALFA Safety Layer
class EnhancedAuthManager:
    """
    Enhanced AuthManager that combines JWT + OpenFGA.

    Use this instead of the basic AuthManager from safety_layer.py
    for production deployments requiring fine-grained authorization.
    """

    def __init__(
        self,
        jwt_secret: str = "hermes-swarm-alfa-secret",
        openfga_url: str = "http://localhost:8080",
    ):
        # Import original AuthManager
        import sys
        sys.path.insert(0, str(__file__).replace("/integration/openfga_adapter.py", "/swarm"))
        from safety_layer import AuthManager as JWTAuthManager

        self.jwt_auth = JWTAuthManager(secret_key=jwt_secret)
        self.fga_auth = OpenFGAAuthAdapter(openfga_url=openfga_url)

    async def initialize(self):
        """Initialize both auth systems."""
        fga_ok = await self.fga_auth.initialize()
        if fga_ok:
            await self.fga_auth.setup_default_permissions()
        return True

    def generate_token(self, agent_id: str, role: str = "operator") -> str:
        """Generate JWT token."""
        return self.jwt_auth.generate_token(agent_id, role)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        return self.jwt_auth.verify_token(token)

    async def check_permission(
        self,
        token: str,
        permission: Permission,
        resource_id: str = "main",
    ) -> AuthorizationResult:
        """Check permission using OpenFGA (with JWT fallback)."""
        # First verify JWT
        payload = self.verify_token(token)
        if not payload:
            return AuthorizationResult(allowed=False, reason="Invalid token")

        user_id = payload.get("agent_id", "unknown")
        jwt_role = payload.get("role", "viewer")

        # Then check OpenFGA
        return await self.fga_auth.check_permission(
            user_id=user_id,
            permission=permission,
            resource_id=resource_id,
            jwt_role=jwt_role,
        )

    async def close(self):
        """Cleanup."""
        await self.fga_auth.close()


# CLI for testing
async def main():
    """Test OpenFGA integration."""
    print("Testing OpenFGA adapter...")

    auth = EnhancedAuthManager()
    await auth.initialize()

    # Generate token for Hermes
    token = auth.generate_token("hermes", "admin")
    print(f"Token: {token[:50]}...")

    # Check permissions
    result = await auth.check_permission(
        token, Permission.SWARM_START
    )
    print(f"Can start swarm: {result.allowed} ({result.reason})")

    result = await auth.check_permission(
        token, Permission.CERBER_CHAOS
    )
    print(f"Can trigger chaos: {result.allowed} ({result.reason})")

    await auth.close()
    print("Done!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
