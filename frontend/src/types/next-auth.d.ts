import "next-auth"
declare module "next-auth" {
  interface Session {
    user: { id?: string; name?: string | null; email?: string | null; image?: string | null; role?: string; accessToken?: string }
    accessToken?: string
  }
  interface User {
    id: string
    name?: string | null
    email?: string | null
    image?: string | null
    role?: string
    accessToken?: string
  }
}
declare module "next-auth/jwt" {
  interface JWT { id?: string; role?: string; accessToken?: string; email?: string; name?: string }
}
