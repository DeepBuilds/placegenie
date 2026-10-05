import client from './client'

const data = (r) => r.data

export const getChatInfo = () => client.get('/chat/info').then(data)
export const sendChatMessage = (message, conversationId) =>
  client
    .post('/chat/messages', { message, conversation_id: conversationId ?? null }, { timeout: 45000 }) // an AI reply can take a while
    .then(data)
export const listConversations = () => client.get('/chat/conversations').then(data)
export const getConversation = (id) => client.get(`/chat/conversations/${id}`).then(data)
export const deleteConversation = (id) => client.delete(`/chat/conversations/${id}`)
export const deleteAllConversations = () => client.delete('/chat/conversations')
