import pytest
import os
from pydantic import ValidationError
from backend.app.config import Settings


def test_matrix_row1_unset_app_env_unset_demo_mode():
    s = Settings(APP_ENV=None, DEMO_MODE=None, ADMIN_PASSWORD="valid_admin_password_123")
    assert s.APP_ENV == "production"
    assert s.DEMO_MODE is True


def test_matrix_row2_production_unset_demo_mode():
    s = Settings(APP_ENV="production", DEMO_MODE=None, ADMIN_PASSWORD="valid_admin_password_123")
    assert s.APP_ENV == "production"
    assert s.DEMO_MODE is True


def test_matrix_row3_production_explicit_demo_mode_true():
    s = Settings(APP_ENV="production", DEMO_MODE="true", ADMIN_PASSWORD="valid_admin_password_123")
    assert s.APP_ENV == "production"
    assert s.DEMO_MODE is True


def test_matrix_row4_production_demo_mode_false_weak_password_fails():
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", DEMO_MODE="false", ADMIN_PASSWORD="change_me_in_env")
    assert "known default placeholder" in str(exc.value)

    with pytest.raises(ValidationError) as exc2:
        Settings(APP_ENV="production", DEMO_MODE="false", ADMIN_PASSWORD="short")
    assert "at least 12 characters" in str(exc2.value)


def test_matrix_row5_production_demo_mode_false_strong_password_succeeds():
    s = Settings(APP_ENV="production", DEMO_MODE="false", ADMIN_PASSWORD="super_secure_admin_pass_2026")
    assert s.APP_ENV == "production"
    assert s.DEMO_MODE is False


def test_matrix_row6_production_invalid_demo_mode_fails():
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", DEMO_MODE="invalid_val", ADMIN_PASSWORD="valid_admin_password_123")
    assert "Invalid DEMO_MODE" in str(exc.value)


def test_matrix_row7_development_unset_demo_mode():
    s = Settings(APP_ENV="development", DEMO_MODE=None, ADMIN_PASSWORD="any")
    assert s.APP_ENV == "development"
    assert s.DEMO_MODE is False


def test_matrix_row8_development_explicit_demo_mode_false():
    s = Settings(APP_ENV="development", DEMO_MODE="false", ADMIN_PASSWORD="any")
    assert s.APP_ENV == "development"
    assert s.DEMO_MODE is False


def test_matrix_row9_development_explicit_demo_mode_true():
    s = Settings(APP_ENV="development", DEMO_MODE="true", ADMIN_PASSWORD="any")
    assert s.APP_ENV == "development"
    assert s.DEMO_MODE is True


def test_matrix_row10_development_invalid_demo_mode_fails():
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="development", DEMO_MODE="unknown_mode", ADMIN_PASSWORD="any")
    assert "Invalid DEMO_MODE" in str(exc.value)


def test_matrix_row11_invalid_app_env_fails():
    for invalid_env in ["staging", "test", "local", "prod", "qa"]:
        with pytest.raises(ValidationError) as exc:
            Settings(APP_ENV=invalid_env, ADMIN_PASSWORD="any_password_123")
        assert "Invalid APP_ENV" in str(exc.value)


def test_matrix_row12_production_empty_admin_password_fails():
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", DEMO_MODE="true", ADMIN_PASSWORD="")
    assert "ADMIN_PASSWORD must be configured and cannot be empty" in str(exc.value)


# --- Item 1: Production password rules enforced regardless of DEMO_MODE ---

def test_matrix_prod_demo_true_weak_password_fails():
    """DEMO_MODE=true must NOT bypass password strength in production."""
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", DEMO_MODE="true", ADMIN_PASSWORD="short")
    assert "at least 12 characters" in str(exc.value)


def test_matrix_prod_demo_true_known_default_fails():
    """DEMO_MODE=true must NOT bypass known-default check in production."""
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", DEMO_MODE="true", ADMIN_PASSWORD="change_me_in_env")
    assert "known default placeholder" in str(exc.value)


def test_matrix_prod_demo_unset_weak_password_fails():
    """DEMO_MODE=None (resolves to True in production) must still reject weak passwords."""
    # "admin" is both short AND a known default — either error message is acceptable.
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", DEMO_MODE=None, ADMIN_PASSWORD="admin")
    assert ("at least 12 characters" in str(exc.value) or "known default placeholder" in str(exc.value))


def test_matrix_prod_demo_true_strong_password_succeeds():
    """A strong password with DEMO_MODE=true in production must succeed."""
    s = Settings(APP_ENV="production", DEMO_MODE="true", ADMIN_PASSWORD="strong_valid_password_123")
    assert s.APP_ENV == "production"
    assert s.DEMO_MODE is True



def test_deprecated_allowed_origins_env_var_fails(monkeypatch):
    """Setting the deprecated ALLOWED_ORIGINS env var must cause a startup error."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://example.com")
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="development", ADMIN_PASSWORD="any")
    assert "ALLOWED_ORIGINS" in str(exc.value)
    assert "deprecated" in str(exc.value).lower()
