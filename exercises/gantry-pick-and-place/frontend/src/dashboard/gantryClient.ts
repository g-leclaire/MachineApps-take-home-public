import { create } from '@bufbuild/protobuf'
import { EmptySchema } from '@bufbuild/protobuf/wkt'
import { createClient } from '@connectrpc/connect'
import { createConnectTransport } from '@connectrpc/connect-web'

import { GantryPickAndPlaceService, TargetPositionsSchema } from '../gen/app_pb'

const transport = createConnectTransport({
  baseUrl: import.meta.env.VITE_RPC_BASE_URL ?? '/rpc',
})

const rpcClient = createClient(GantryPickAndPlaceService, transport)

export const gantryClient = {
  getState: () => rpcClient.getState(create(EmptySchema)),
  telemetryStream: (signal: AbortSignal) =>
    rpcClient.telemetryStream(create(EmptySchema), { signal }),
  getTargetPositions: () => rpcClient.get_target_positions(create(EmptySchema)),
  setTargetPositions: (cubePosition: number[], destinationPosition: number[]) =>
    rpcClient.set_target_positions(create(TargetPositionsSchema, { cubePosition, destinationPosition })),
  home: () => rpcClient.trigger_Home(create(EmptySchema)),
  startSequence: () => rpcClient.trigger_Begin_sequence(create(EmptySchema)),
}