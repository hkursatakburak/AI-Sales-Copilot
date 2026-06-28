// Eklenti yapılandırması. Backend adresi tek bir yerde tutulur ki
// üretime geçerken yalnızca burayı (ve manifest host_permissions'ı) değiştirelim.
const CONFIG = {
  BACKEND_URL: "http://localhost:8000",
  ANALYZE_ENDPOINT: "/analyze",
};
