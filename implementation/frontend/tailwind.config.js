/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
        extend: {
            colors: {
                dark: {
                    900: "#0f172a",
                    800: "#1e293b",
                    700: "#334155",
                },
            },
            animation: {
                "pulse-smooth":
                    "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            },
        },
    },
    plugins: [],
};
