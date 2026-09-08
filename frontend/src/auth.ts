import type { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"

// Mock user DB — thay bằng DB thật khi cần
const USERS = [
  { id: "1", name: "Nhà đầu tư Demo", email: "demo@finsight.vn", password: "demo123", image: "" },
  { id: "2", name: "Admin", email: "admin@finsight.vn", password: "admin123", image: "" },
]

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Đăng nhập",
      credentials: {
        email: { label: "Email", type: "email", placeholder: "demo@finsight.vn" },
        password: { label: "Mật khẩu", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null
        const user = USERS.find((u) => u.email === credentials.email && u.password === credentials.password)
        if (!user) return null
        return { id: user.id, name: user.name, email: user.email, image: user.image }
      },
    }),
  ],
  session: { strategy: "jwt", maxAge: 60 * 60 * 24 * 7 },
  pages: { signIn: "/login" },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
      }
      return token
    },
    async session({ session, token }) {
      if (token && session.user) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (session.user as any).id = token.id
      }
      return session
    },
  },
  secret: process.env.NEXTAUTH_SECRET || "finsight-dev-secret-change-me",
}
