import cv2
import numpy as np

from tile import Tile

hard_colors = {
    (30.0, 30.0, 30.0): 0,
    (90.0, 90.0, 90.0): 1}

expert_colors = {
    (30.0, 30.0, 30.0): 0,
    (40.0, 40.0, 40.0): 1,
    (50.0, 50.0, 50.0): 2,
    (70.0, 70.0, 70.0): 3,
    (80.0, 80.0, 80.0): 4,
    (90.0, 90.0, 90.0): 5
}

# iPhone Mirroring renders the Grayscale scheme with other shades: median gray of a tile for each state
ios_gray_levels = {
    2: [18, 75],  # Hard uses the darkest and lightest Expert shades, like on Android
    6: [18, 29, 39, 51, 62, 75]
}


def find_circles(image: np.ndarray) -> (np.ndarray, list[list]):
    y, x, _ = image.shape
    # print(x, y)

    image = cv2.medianBlur(image, 1)

    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    circles = cv2.HoughCircles(gray_image, cv2.HOUGH_GRADIENT, 1, 25, param1=10, param2=29, minRadius=42, maxRadius=44)
    circles = np.uint16(np.around(circles))[0].tolist()

    return image, circles


def top_of_leftmost_column(circles: list[list]) -> list:
    # columns are ~80px apart, so everything within 20px of the leftmost x is the same column
    # (rounding x to tens split a column whose centers jittered between 84 and 86)
    min_x = min(circle[0] for circle in circles)
    return min((circle for circle in circles if circle[0] - min_x < 20), key=lambda x: x[1])


def sort_circles_to_grid(circles: list[list]) -> list[list]:
    # sorting points to right indexes
    start_point = top_of_leftmost_column(circles)

    start_x = start_point[0]
    start_y = start_point[1]

    sorted_circles = [start_point]
    circles.remove(start_point)
    index = 0
    misses = 0

    while len(circles) != 0:
        # up-right neighbour; 70 is for iOS where tiles are ~78px apart after scaling
        if round(start_y - circles[index][1], -1) in (40, 50) and round(circles[index][0] - start_x, -1) in (70, 80, 90):
            start_y = circles[index][1]
            start_x = circles[index][0]
            sorted_circles.append(circles[index])
            circles.remove(circles[index])
            misses = 0
        if len(sorted_circles) in (4, 9, 15, 22, 28, 33):
            start_x, start_y, _ = top_of_leftmost_column(circles)
            sorted_circles.append([start_x, start_y, _])
            circles.remove([start_x, start_y, _])
            misses = 0
        index += 1
        misses += 1
        if misses > 2 * len(circles) + 2:
            raise RuntimeError(f"could not sort circles into the grid, stuck after {len(sorted_circles)} tiles")
        if index >= len(circles):
            index = 0

    return sorted_circles


def is_solved(image, circles: list[list]) -> bool:
    # a solved board is drawn with one uniform fill on every tile
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fills = []
    for circle in circles:
        circle_img = np.zeros(gray_image.shape, np.uint8)
        cv2.circle(circle_img, (circle[0], circle[1]), circle[2], 255, -1)
        fills.append(np.median(gray_image[circle_img > 0]))
    return max(fills) - min(fills) < 5


def get_grid_with_colors(image, circles: list[list], mode: int, platform: str = "android") -> list[Tile]:
    grid = []

    colors = hard_colors if mode == 2 else expert_colors
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    for i in range(len(circles)):
        circle = circles[i]
        # draw the outer circle
        circle_img = np.zeros((image.shape[0], image.shape[1]), np.uint8)
        cv2.circle(circle_img, (circle[0], circle[1]), circle[2], (255, 255, 255), -1)
        if platform == "ios":
            # median ignores the arrow or number drawn on the tile, so it works in both display modes
            gray = np.median(gray_image[circle_img > 0])
            levels = ios_gray_levels[mode]
            color_index = min(range(mode), key=lambda k: abs(levels[k] - gray))
        else:
            # get average color
            color = cv2.mean(image, mask=circle_img)[:3]
            color = tuple([round(i, -1) for i in color])
            color = (70.0, 70.0, 70.0) if color == (60.0, 60.0, 60.0) else color
            color_index = colors[color]
        grid.append(Tile(circle[0], circle[1], color_index))
        cv2.circle(image, (circle[0], circle[1]), circle[2], (0, 255, 0), 2)
        cv2.putText(image, f"{i}", (circle[0] - 13, circle[1] + 10), 2, 1, (255, 255, 255))

    # cv2.imshow('detected circles', image)
    # cv2.waitKey(0)

    return grid


if __name__ == "__main__":
    photo = cv2.imread("images/screen.jpg")
    formatted_image, circles_list = find_circles(photo)
    sorted_circles_list = sort_circles_to_grid(circles_list)
    colors_list = get_grid_with_colors(formatted_image, sorted_circles_list, 2)
    for i in range(len(colors_list)):
        print(i, colors_list[i])
