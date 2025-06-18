import random
import string
from typing import Optional, ClassVar
from django_redis import get_redis_connection
from redis import Redis
from django.http import HttpRequest


class TempLoginCodeManager:
    CODE_PREFIX: ClassVar[str] = "temp_login_code:"
    SESSION_PREFIX: ClassVar[str] = "temp_login_session:"
    EXPIRE_MINUTES: ClassVar[int] = 10

    @staticmethod
    def generate_code() -> str:
        """임시 로그인 코드 생성 (영문1 + 숫자5)"""
        return random.choice(string.ascii_uppercase) + "".join(
            random.choices(string.digits, k=5)
        )

    @classmethod
    def create_login_session(cls, request: HttpRequest) -> str:
        """
        임시 로그인 세션 생성 및 코드 반환

        Args:
            request: Django request 객체

        Returns:
            생성된 임시 로그인 코드
        """
        redis_client: Redis = get_redis_connection("default")
        code: str = cls.generate_code()

        # 새로운 세션 생성
        request.session.create()
        session_key: str = request.session.session_key

        # Redis에 코드와 세션 키 매핑 저장
        redis_client.setex(
            f"{cls.CODE_PREFIX}{code}", cls.EXPIRE_MINUTES * 60, session_key
        )

        # 세션에도 임시 코드 상태 표시
        request.session["temp_login_code"] = code
        request.session.set_expiry(cls.EXPIRE_MINUTES * 60)

        return code

    @classmethod
    def verify_and_login(cls, request: HttpRequest, code: str, user_id: str) -> bool:
        """
        코드 확인 및 실제 사용자 로그인 처리

        Args:
            request: Django request 객체
            code: 임시 로그인 코드
            user_id: 실제 사용자 ID

        Returns:
            로그인 성공 여부
        """
        redis_client: Redis = get_redis_connection("default")
        key: str = f"{cls.CODE_PREFIX}{code}"

        # 코드로 세션 키 가져오기
        session_key: Optional[bytes] = redis_client.get(key)

        if not session_key:
            return False

        session_key_str: str = session_key.decode("utf-8")

        # 현재 세션이 일치하는지 확인
        if request.session.session_key != session_key_str:
            return False

        # 임시 코드 관련 데이터 삭제
        redis_client.delete(key)
        if "temp_login_code" in request.session:
            del request.session["temp_login_code"]

        # 실제 사용자 ID를 세션에 저장
        request.session["user_id"] = user_id
        request.session.set_expiry(0)  # 브라우저 종료 시 세션 만료

        return True

    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        """
        코드 유효성 확인

        Args:
            code: 확인할 임시 로그인 코드

        Returns:
            코드의 유효성 여부
        """
        redis_client: Redis = get_redis_connection("default")
        return bool(redis_client.exists(f"{cls.CODE_PREFIX}{code}"))
