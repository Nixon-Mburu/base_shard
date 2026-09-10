import React from "react";
export default function ProductArt({ product: p }) {
  const bottle = ["oil", "soap"].includes(p.icon);
  return (
    <svg
      viewBox="0 0 240 160"
      className="product-art"
      role="img"
      aria-label={p.name}
    >
      <ellipse cx="120" cy="144" rx="56" ry="7" fill="#000" opacity=".06" />
      {bottle ? (
        <>
          <path
            d="M101 25h38v19l18 15v73q0 9-9 9H92q-9 0-9-9V59l18-15Z"
            fill={p.color}
          />
          <rect x="99" y="17" width="42" height="13" rx="3" fill="#6e389e" />
          <path
            d="M141 52h15v29h-11"
            fill="none"
            stroke={p.color}
            strokeWidth="11"
          />
        </>
      ) : (
        <>
          <path
            d="M79 28Q120 19 161 28L168 137Q120 150 72 137Z"
            fill={p.color}
          />
          <path
            d="M80 30q40 9 80 0M75 133q45 10 90 0"
            fill="none"
            stroke="#fff"
            strokeWidth="3"
            opacity=".6"
          />
        </>
      )}
      <rect
        x="86"
        y="64"
        width="68"
        height="51"
        rx="3"
        fill="white"
        opacity=".93"
      />
      <text
        x="120"
        y="79"
        textAnchor="middle"
        fill="#7138cf"
        fontFamily="Gabarito"
        fontSize="9"
        fontWeight="700"
      >
        BASE SELECT
      </text>
      <text
        x="120"
        y="96"
        textAnchor="middle"
        fill="#32303a"
        fontFamily="Gabarito"
        fontSize="13"
        fontWeight="700"
      >
        {p.icon.toUpperCase()}
      </text>
      <text
        x="120"
        y="108"
        textAnchor="middle"
        fill="#6f6878"
        fontFamily="Gabarito"
        fontSize="6"
      >
        QUALITY FOR YOUR EVERYDAY
      </text>
    </svg>
  );
}
