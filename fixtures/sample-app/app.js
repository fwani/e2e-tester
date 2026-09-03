// 픽스처 앱 상태. localStorage 로 화면 간 상태를 유지한다.
const KEY = 'itb-fixture-projects';
const SEED = [
  { name: '주간 리텐션', created: '2일 전', status: '활성' },
  { name: '이탈 코호트', created: '1주 전', status: '보관' },
];

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : SEED.slice();
  } catch {
    return SEED.slice();
  }
}
function save(list) {
  try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { /* 저장 실패는 무시 */ }
}
function isLoggedIn() {
  try { return sessionStorage.getItem('itb-fixture-auth') === '1'; } catch { return false; }
}
function requireLogin() {
  if (!isLoggedIn()) location.replace('login.html');
}
