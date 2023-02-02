from scripts.classes.contracts import ClientFactory
import code;


def main():
    client = ClientFactory.getInstance()
    client.sendFunds(1e+19)
    request = client.createRequest(client.encodeInput(1, [10]))
    print(f"RequestID: {request.id}")
    request = client.createRequest(client.encodeInput(2, [20]))
    print(f"RequestID: {request.id}")
    code.interact(local=dict(globals(), **locals()))

if __name__ == "__main__":
    main()
