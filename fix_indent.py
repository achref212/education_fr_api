import re

with open('tests/test_auth_service.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('    def test_'):
        new_lines.append(line[4:])
    elif line.startswith('        svc, users'):
        new_lines.append(line[4:])
    elif line.startswith('        users.create_user'):
        new_lines.append(line[4:])
    elif line.startswith('            email="alice@gmail.com"'):
        new_lines.append(line[4:])
    elif line.startswith('            password_hash=hash_password'):
        new_lines.append(line[4:])
    elif line.startswith('            first_name="Alice"'):
        new_lines.append(line[4:])
    elif line.startswith('            last_name="B"'):
        new_lines.append(line[4:])
    elif line.startswith('            level="2e"'):
        new_lines.append(line[4:])
    elif line.startswith('            is_active=True'):
        new_lines.append(line[4:])
    elif line.startswith('        )'):
        new_lines.append(line[4:])
    elif line.startswith('        repo = FakeUserRepo()'):
        new_lines.append(line[4:])
    elif line.startswith('        auth = AuthService(repo)'):
        new_lines.append(line[4:])
    elif line.startswith('        auth.register('):
        new_lines.append(line[4:])
    elif line.startswith('            password="rightpass"'):
        new_lines.append(line[4:])
    elif line.startswith('        # Manually activate user for login test'):
        new_lines.append(line[4:])
    elif line.startswith('        user = repo.get_by_email("alice@gmail.com")'):
        new_lines.append(line[4:])
    elif line.startswith('        if user:'):
        new_lines.append(line[4:])
    elif line.startswith('            repo.activate_user(user.user.id)'):
        new_lines.append(line[4:])
    elif line.startswith('            '):
        new_lines.append(line[4:])
    elif line.startswith('        with pytest.raises(AuthError):'):
        new_lines.append(line[4:])
    elif line.startswith('            auth.login("alice@gmail.com", "wrong")'):
        new_lines.append(line[4:])
    else:
        new_lines.append(line)

with open('tests/test_auth_service.py', 'w') as f:
    f.writelines(new_lines)
