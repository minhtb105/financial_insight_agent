import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/auth"
import { ChatContainer } from "@/components/chat/ChatContainer"

export default async function ChatPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect("/login")
  return <ChatContainer />
}
