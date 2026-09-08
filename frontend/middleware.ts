export { default } from "next-auth/middleware"
export const config = { matcher: [] }
// Auth protection handled via getServerSession in pages to keep middleware minimal for now
