import { ImageResponse } from "next/og";

// Configuración del segmento de ruta
export const runtime = "edge";

// Metadatos de la imagen del icono
export const size = {
  width: 32,
  height: 32,
};
export const contentType = "image/png";

// Generación dinámica del icono (Favicon)
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 20,
          background: "linear-gradient(135deg, #2563eb, #7c3aed)",
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "8px",
          color: "white",
        }}
      >
        🎙️
      </div>
    ),
    {
      ...size,
    }
  );
}
