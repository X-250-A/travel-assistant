import type { Metadata } from "next";
import { AuthProvider } from "@/hooks/useAuth";
import "./globals.css";

export const metadata: Metadata = {
  title: "旅游助手",
  description: "面向国内游的行程规划智能体",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col antialiased text-gray-900">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
