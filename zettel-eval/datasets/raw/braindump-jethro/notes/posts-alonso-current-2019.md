## Current Research Trends in Robot Grasping and Bin Picking

### Robot Grasping

### Traditional Bin-picking Approaches

Most algorithms rely on segmentation of RGB-D data. 3D object recognition is done by matching 3D data to their known CAD models. [Interactive Closest Point](https://braindump.jethro.dev/posts/interactive_closest_point) can be used to calculate the alignment and best fitting of a cloud of points with respect to a reference CAD model.

A fast voting scheme similar to the Generalized Hough Transform can be used improving the performance of [ICP](https://braindump.jethro.dev/posts/interactive_closest_point).

### Deep Learning Methodologies for Bin Picking

Deep Learning approaches used RGB-D images as input, and are able to predict grasp success and generalize to novel objects.
