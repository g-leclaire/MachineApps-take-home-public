import { create } from '@bufbuild/protobuf'
import { EmptySchema } from '@bufbuild/protobuf/wkt'
import { createClient } from '@connectrpc/connect'
import { createConnectTransport } from '@connectrpc/connect-web'

import { GantryPickAndPlaceService } from '../gen/app_pb'

const transport = createConnectTransport({
  baseUrl: import.meta.env.VITE_RPC_BASE_URL ?? '/rpc',
})

const rpcClient = createClient(GantryPickAndPlaceService, transport)

export const gantryClient = {
  getState: () => rpcClient.getState(create(EmptySchema)),
  machineStatusStream: (signal: AbortSignal) =>
    rpcClient.machineStatusStream(create(EmptySchema), { signal }),
  startSequence: () => rpcClient.trigger_Begin_sequence(create(EmptySchema)),
}