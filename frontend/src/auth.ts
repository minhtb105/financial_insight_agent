import type { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import bcrypt from "bcryptjs"

// Hashed passwords (bcrypt 10 rounds) — plaintext demo123/admin123 not stored
const USERS = [
  { id: "1", name: "Nhà đầu tư Demo", email: "demo@finsight.vn", passwordHash: "$2b$10$fc8p0891RUEZVzl/c9OXk.I.bJqH4uOTZa.T/FXRA8GoA.yiK7PmO", image: "" },
  { id: "2", name: "Admin", email: "admin@finsight.vn", passwordHash: "$2b$10$Y2i3DPSwLD7SxKMTDVc9beI1ymYltCvtE5gvvptJbXPwKb3I0RMfC", image: "" },
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
        const user = USERS.find((u) => u.email === credentials.email)
        if (!user) return null
        const ok = await bcrypt.compare(credentials.password, user.passwordHash)
        if (!ok) return null
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
  secret: process.env.NEXTAUTH_SECRET || (process.env.NODE_ENV === "production" ? (() => { throw new Error("NEXTAUTH_SECRET must be set in production") })() : "finsight-dev-secret-change-me"),
}
