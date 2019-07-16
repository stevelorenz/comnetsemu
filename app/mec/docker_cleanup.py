import docker
import time


def cleanup() -> bool:
    """
    stop all actively running containers\n
    (this does not remove put to sleep containers, yet)

    :return: None
    """

    try:
        client = docker.from_env()

        images = client.images.list()
        print(f"found {images.__len__()} images")
        for img in images:
            img = str(img)
            if "dev_test" in img:
                print("found \"dev_test\"")
                break
        else:
            raise Exception

        containers = client.containers.list()  # consider supplementing cleanup with "docker rm $(docker ps -aq)"
        print(f"found {containers.__len__()} containers")
        for container_id in containers:
            container_id = str(container_id).replace(">", "").split(" ")[1]
            container = client.containers.get(container_id=container_id)
            print(f"putting container {container_id} to sleep . . .")
            container.stop()
            time.sleep(2)

            return True

    except Exception:
        return False

