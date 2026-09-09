import type { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import { getBackendUrl } from "@/lib/backend"

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
        try {
          const res = await fetch(`${getBackendUrl()}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: credentials.email, password: credentials.password }),
          })
          if (!res.ok) return null
          const data = await res.json()
          const user = data.user
          if (!user) return null
          return {
            id: user.id,
            name: user.name || user.email,
            email: user.email,
            image: "",
            role: user.role,
            accessToken: data.access_token,
          } as unknown as { id: string; name: string; email: string; image: string }
        } catch {
          return null
        }
      },
    }),
  ],
  session: { strategy: "jwt", maxAge: 60 * 60 * 24 * 7 },
  pages: { signIn: "/login" },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        const u = user as unknown as { id: string; role?: string; accessToken?: string; email?: string; name?: string }
        token.id = u.id
        token.role = u.role
        token.accessToken = u.accessToken
        if (u.email) token.email = u.email
        if (u.name) token.name = u.name
      }
      return token
    },
    async session({ session, token }) {
      if (token && session.user) {
        const t = token as unknown as { id?: string; role?: string; accessToken?: string }
        session.user.id = t.id
        session.user.role = t.role
        session.user.accessToken = t.accessToken
        ;(session as unknown as { accessToken?: string }).accessToken = t.accessToken
      }
      return session
    },
  },
  secret: process.env.NEXTAUTH_SECRET || "finsight-dev-secret-change-me",
}
